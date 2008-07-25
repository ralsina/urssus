"""easylog wraps the logging module, to reduce the required glue.

The standard logging module is very useful, but it does not easily
scale *down* for simple uses.  easylog provides the required
configuration and glue code, so that scripts and application modules
can treat logging as a one-liner,

Sample Lightweight Usage
========================

    >>> from easylog import critical, error, warning, debug, info
    >>> debug("getFoo requesting %d %s", 42, "answers")
    >>> error("getFoo says %d of those %s are lousy!", 19, "answers")
    ERROR:easylog.easylog:getFoo says 19 of those answers are lousy!

The debug message is captured in (current directory) file EasyLogA,
but is not echoed to the screen.  The error message goes both places.


Sample Midweight Usage
======================

If you want slightly more control, you can use more of the easylog
API.  Additional examples can be found in the default setup at the
bottom of this file.

    >>> import easylog
    >>> from easylog import debug, info, warn, error, fatal
    
    >>> # log as MyApp, regardless of the current filename.
    ... # ignore debug messages.
    ... easylog.setLogger(name='MyApp', level=easylog.INFO)
    <easylog.easyLogger instance at 0x813207c>
    
    >>> # messages from "mytrace" are really from its caller.
    ... easylog.ignoreCaller("mytrace")

    >>> warn("Debug messages will be sent but ignored.")

The default configuration sends all messages to a rotating logfile.
(EasyLogA in the current directory)

The default configuration also echoes important messages to the
standard error stream.  fatal or critical messages are always
important.  Errors are important, but are filtered to prevent
repeats of the exact same message.  Warnings are important, but
are not repeated even if the parameters (such as which file is
missing) change.


Specialized Usage
=================

If you want even more control, then importing * should expose
(a superset of) all functionality available through the underlying
logging package, with the following restrictions:

    (1)  All easylog calls other than "disable" are rooted
         on (virtual root) logging.root.easylog,rather than
         directly on logging.root.

         This reduces (but does not eliminate) interference
         from other processes using the same logging system.

    (2)  Direct manipulation of the logging tree is not supported.

By using easylog instead of using the underlying logging package
directly, you will still gain these advantages.

All paramaters which can be set through either a logging config file
or set* functions can be set through keyword arguments to the initial
class constructor.  This is true even when the underlying library does
not support configuration at construction time.

Most parameters that can be set at initial construction can be changed
later through a set* function.  This is sometimes true even when the
underlying library does not support reconfiguration.


Naming conventions
==================

The logging package uses:

    MixedCase for classes
    camelCase for functions and methods
    UPPER_CASE for global variables.

easylog follows this convention, but does expose global functions
under the lower_case alias to support the recommended python style.
Class methods are not usually given aliases; you will still need to
use camelCase.


Notable extensions to the logging API
=====================================

addLevelName (level, levelname)
-------------------------------

add_level_name(5, "DEBUG_VERBOSE") creates a DEBUG_VERBOSE constant
for the log function and for display or use with filter functions.
The easylog version also creates a debug_verbose convenience function.

add_level_name is an alias.


ignoreCaller(filename)
-----------------

Treat name as part of the logging system.  Functions in this file/module
are ignored when determining where a logging message originated.

ignore_caller is an alias.


setLogger(name=None, level=None, handlers=None, propagate=None)
===============================================================

This overrides logging getLogger, but the set name is preferred,
as several options can be changed.  If an argument is None or
is not passed, the previous value will be kept.  If this is a
new logger, the default values will be used.

getLogger, set_logger, and get_logger are all aliases.


FilterUnique(minLevel=None, maxLevel=None, exact=False, hide=None)
==================================================================

Creates a filter to suppress duplicate messages.

Messages of importance less than minLevel or greater than maxLevel
are ignored; they will be filtered or approved by other functions.

If exact is True, then messages will only be suppresed if they match
exactly *after* string interpolation of any additional arguments.
If exact is False, the messages will be considered duplicate even if
the values of the parameters change::

    error("Bad Value: %d", 5)
    error("Bad Value: %d", -43)

are the same if exact is False, but different if exact is True.

hide is a dictionary of already-seen messages.  The default is to
create a new empty dictionary when the filter is constructed.

minLevel and maxLevel can also be spelled min_level and max_level.

If there is no max_level, the default is equal to the min_level.


DefaultConsole
==============

Important messages are sent to Standard Error.  Important means
unique WARNINGs, exactly unique ERRORs, and any CRITICAL or FATAL errors.


DefaultLogFile
==============

All messages are logged here, unless a user has in some way explicitly
suppressed them.


"""

import sys
import logging
import types
from os.path import split, splitext, basename, normcase

try:
    from atexit import register as register_exit
except ImportError:
    def register_exit(fn):
        oldexit = sys.exit
        def exithook(*args, **kwargs):
            fn()
            oldexit(*args, **kwargs)
        sys.exit = exithook
    

# __all__ will be extended by names exported from the underlying logging
# and logging.handlers packages, including convenience functions,
# handlers and level-names
__all__ = []


__copyright__ = """Copyright 2004, Jim J. Jewett.  All rights reserved.

easylog is licensed under the Python Software Foundation license.

Please send any comments or patches to JimJJewett@yahoo.com, or see
<URL: http://sourceforge.net/projects/easylog >

"""

__version__ = (0, 2, 0, "alpha1", 0)

loggers = {}

# grep for lines starting with 'levelname 20' to find when they were logged
# grep for lines starting with 'levelname fr' to find the source file/line
# grep for lines starting with 'levelname: ' to find the actual messages.
#
# If filenames and messages are reasonably short, then the log will fit
#    in 80 characters without linewrap.
EXTENDED_FORMAT = ("%(levelname)s %(asctime)s " +
                      "in thread %(process)d.%(thread)d\n" +
                   "%(levelname)s from %(name)s file %(filename)s " +
                      "line %(lineno)d\n" +
                   "%(levelname)s: %(message)s\n")

########################################################################
#
# For compatibility with python versions < 2.3
#
########################################################################
try:
    (True, False)
except NameError:
    # match the 2.2 definition
    (True, False) = (1, 0)

def dictpop(d, k, default=None):
    """dict.pop() is new in 2.3"""
    try:
        ret = d.pop(k, default)
    except AttributeError:
        try:
            ret = d[k]
            del d[k]
        except KeyError:
            ret = default
    return ret


########################################################################
#
# code templates, used for statements which depend on the contents
# of other modules.  Use of templates provides some small degree
# of protection against changes in the underlying library.
#
########################################################################

convenience_fn_string = (
"""
def %(levelLow)s(*args, **kwargs):
    chooseLogger().%(levelLow)s(*args, **kwargs)
    
exec("globals()['%(levelLow)s'] = %(levelLow)s")    

"""
)

handler_mixin_string = (
"""
class %(name)s(%(parentClass)s):
    '''%(name)s augments %(parentClass)s with set methods and init keywords.'''
    
    # Note that we cannot use super(thisclass, self) because logging.Handler 
    # does not inherit from object.  Even if we add object as a base, we are
    # just asking for trouble if our own parent classes are not designed as
    # new style classes.

    # class-wide defaults
    msg_fmt = None
    time_fmt = None
    formatclass = logging.Formatter

    def __init__(self, *args, **kwargs):
        '''logging message handler %(name)s

        level is the minimum level that is not ignored.
        formatter is the formatting function.
        fmt or format is the format string used by formatter.
        datefmt or dateformat is the date/time formatting string.
        If any element of filters returns False, the message is suppressed.
        
        '''
        # Using kwargs directly fails when we split out the formatting
        # portion, as **kwargs passes a copy, so that the keywords are
        # not removed from the original kwargs -- and they are still
        # there to the detriment of the parent class.
        self._ini = kwargs
        level = dictpop(self._ini, 'level', None)
        filters = dictpop(self._ini, 'filters', [])

        # Call this before parent.__init__ to remove the keywords.
        # But the parent may explicitly set formatter to None, and then
        # use its own default ... so we have to save the result.
        self.setFormat()
        __tempfmt = self.formatter

        # Note that we pass through any unrecognized arguments; the
        # standard logging module will raise an exception if it does 
        # not understand them either.
        %(parentClass)s.__init__(self, *args, **self._ini)

        self.formatter = __tempfmt
        if level:
            self.setLevel(level)
        for f in filters:
            self.addFilter(f)

    def setFormat(self, **kwargs):
        '''If format or dateformat was passed, use it.

        Otherwise use the current value.  If there is no current value,
        then fall through to the default of the parent class.  Note that
        this assumes the Formatter API, though it does go through
        contortions to work with BufferingFormatter or a Formatter which
        takes no parameters.

        '''
        self._ini.update(kwargs)
        self.formatclass = dictpop(kwargs, 'formatter',
                                   self.formatclass)
        self.msg_fmt = (dictpop(self._ini, 'fmt', None) or
                        dictpop(self._ini, 'format', None) or
                        dictpop(self._ini, 'linefmt',
                                self.msg_fmt))
        self.time_fmt = (dictpop(self._ini, 'datefmt', None) or
                         dictpop(self._ini, 'dateformat',
                                 self.time_fmt))

        # Do not pass an explicit None, as BufferingFormatter chokes on
        # the second (date format) argument.
        if self.time_fmt:
            self.setFormatter(self.formatclass(self.msg_fmt, self.time_fmt))
        elif self.msg_fmt:
            self.setFormatter(self.formatclass(self.msg_fmt))
        else:
            self.setFormatter(self.formatclass())            

    def close(self):
        '''ensure flush() before close.  Call me paranoid.'''
        try:
            self.flush()
        except ValueError:
            pass
        %(parentClass)s.close(self)
"""
)

########################################################################
#
# Specific overrides of module-level symbols.
#
########################################################################

# The easylog classes do not inherit from this improved Filterer, but
# we make it available so that our own callers can use the "create it
# right in the first place" API that we export for other classes.
# Note that the only recognized argument is filters -- anything else
# will be passed through and therefore will create an exception.
class Filterer(logging.Filterer):
    def __init__(self, filters=None, *args, **kwargs):
        logging.Filterer.__init__(self, *args, **kwargs)
        if filters:
            for filter in filters:
                self.addFilter(filter)

# In addition to calling logging.addLevelName, we also provide the
# expected convenience functions.
# By convention, levelnames are all caps, and convenience functions
# are all lower case.  An all-lower-case level-name will be shadowed
# by its convenience function.
def addLevelName(level, levelName, knownname=False):
    if not knownname:
        logging.addLevelName(level, levelName)
    varset = {'levelName': levelName,
              'levelLow' : levelName.lower(),
              'levelno': level}
    exec ("globals()['%(levelName)s'] = %(levelno)d" % varset)
    exec(convenience_fn_string % varset)
    exec("globals()['%(levelLow)s'] = %(levelLow)s" % varset)
    __all__.extend((levelName,
                    levelName.lower()))

add_level_name = addLevelName

def shutdown():
    """Safely shut down logging.

    Earlier versions of logging (including that distributed with
    python 2.3) required that the user call logging.shutdown()
    exactly once.  The current library is safer, but this will
    work regardless of version.
    
    The guard clause protects against someone else calling it first.
    The clear protects against repeated calls.

    """
    if logging._handlers:
        logging.shutdown()
        logging._handlers.clear()

register_exit(shutdown)

########################################################################
#
# imports of module level sybmols
#
########################################################################
aliases = ['setLogger', 'set_logger', 'get_logger',
           'add_level_name', 'get_level_name',
           'make_log_record',
           'ignoreCaller']

newdefs = ['EXTENDED_FORMAT',
           'ignore_caller',
           'FilterUnique',
           'DefaultConsole',
           'DefaultLogFile']
new_convenience_functions = ['addHandler', 'removeHandler', 'setHandlers']
nonlevel_convenience_functions = ['exception', 'log']
overridden = ['getLogger',
              'addLevelName',
              'shutdown',
              'Filterer']
passthrough = ['makeLogRecord', 'LogRecord',
               'getLevelName',
               'BASIC_FORMAT',
               'disable']
skipped = ['Logger', 'Manager', 'PlaceHolder', 'setLoggerClass',
           'RootLogger', 'root',
           'Filter',
           'NOTSET', 'raiseExceptions', 
           'basicConfig']

redefined = (newdefs +
             new_convenience_functions +
             nonlevel_convenience_functions +
             overridden)

# These exist, because easylog defines them.
# names in passthrough *should* exist, but we'll wait until we're sure.
__all__.extend(redefined + aliases)

ignored = redefined + skipped 

leftovers=[]
phantoms=[]

# import most of logging (levels, convenience functions)
for (k, v) in vars(logging).items():
    # These names should not exist in the underlying logging package.
    if k in aliases:
        phantoms.append(k)
        continue
    # These we either replace or do not expose
    if k in ignored:
        continue
    if k in passthrough:
        exec ("from logging import %s" % k)
        __all__.append(k)
        continue

    # Do not export private or internal variables
    if k.startswith('_'):
        continue
    # Do not export other modules
    if isinstance(v, types.ModuleType):
        continue

    # Should we add set methods?  Maybe not useful.  Also note
    # that Formatter and BufferingFormatter already have different
    # API and internal variables; the simplicity would be synthetic.
    # Within a handler, we change Formatter options by creating an
    # entirely new object.
    if k.endswith('Formatter'):
        exec("from logging import %s" % k)
        __all__.append(k)
        continue

    # FileHandler, StreamHandler, and the abstract base class Handler
    if k.endswith('Handler'):
        exec(handler_mixin_string %
             {'name': k, 'parentClass': ("logging.%s" % k) })
        __all__.append(k)
        continue
    
    # These should be levelnames, such as debug/DEBUG or warn/WARN.
    # We replace these functions/variables.
    if k == k.lower() and k.upper() in vars(logging):
        continue
    
    # All levelnames (so far) are in all_caps
    if k in logging._levelNames:
        addLevelName(v, k, True)
        continue

    # special case -- logging forgot to include the alias in _levelnames,
    # but if we add it, then it becomes the primary name.  So we add it
    # another way.  When the underlying package is new enough to correct
    # this, then it will be caught by the previous case, and this
    # branch will become dead code.
    if k == 'FATAL':
        addLevelName(v, k, True)
        logging._levelNames[k] = v
        continue
        
    # If the code gets here, then the logging module is newer (or at
    # least different) than expected; log a debug message later.
    leftovers.append((k,v))
    
for newfn in new_convenience_functions:
    exec(convenience_fn_string % {'levelLow': newfn})
    
try:
    import logging.handlers
    handler_list = [handler
                    for handler in vars(logging.handlers)
                    if handler.endswith('Handler')]

    for k in handler_list:
        exec(handler_mixin_string %
             {'name': k, 'parentClass': ("logging.handlers.%s" % k) })

    __all__.extend(handler_list)
    
except ImportError:
    pass

########################################################################
#
#  symbols added by the easylog library.
#
########################################################################

get_level_name = getLevelName
make_log_record = makeLogRecord

def name_as_module (name):
    name = basename(name)
    name = splitext(name)[0]
    return name
    
# These "callers" are really part of the logging system.
# Get *their* callers.
fake_callers = ["<stdin>", "<string>", 'easylog']

def ignore_caller(name):
    """Add a __file__ to the ignore list."""
    if name not in fake_callers:
        fake_callers.append(name)
        shortname = name_as_module (name)
        if shortname not in fake_callers:
            fake_callers.append(name)

ignoreCaller = ignore_caller

try:
    ignore_caller(__file__)
except NameError:
    pass
try:
    ignore_caller(logging.__file__)
except AttributeError:
    pass
try:
    ignore_caller(logging._srcfile)
except AttributeError:
    pass
try:
    ignore_caller(logging.handlers.__file__)
except AttributeError:
    pass


def fake_caller(name):
    """Is this "caller" really part of the logging system?"""
    if name in fake_callers or name_as_module(name) in fake_callers:
        return True
    
    (path, name) = split(name)
    if normcase(path).endswith('logging'):
        return True

    return False

unknown_file_name = "<unknown file>"
def findLogCaller():
    """Return source filename (and line number) of the caller.
    
    Based on logging.Logger().findCaller(), but excludes easylog as well.
    
    """
    try:
        f = sys._getframe(1)
        while True:
            co = f.f_code
            filename = co.co_filename
            if fake_caller(filename):
                f = f.f_back
                continue
            return filename, f.f_lineno
    # The logging module suggests that _getframe may not exist (despite
    # the documentation).  We could also reach the top frame (so that
    # there is no f_back) and still be in excluded files.
    except (AttributeError, ValueError):
        return unknown_file_name, 0

def chooseLogger(name=None):
    """Which logger should this caller use?"""

    # Who called?
    if name is None:
        name, ignored = findLogCaller()

    # Normalize the name.
    if name == unknown_file_name:
        name = 'easylog'
    else:
        name = "easylog." + name_as_module(name)

    # Does the caller already have a logger?  Use our dict
    # first, so that a multi-file app can easily send all
    # output to a single logger by calling
    # setLogger(name="myapp") in each file.
    try:
        logger = loggers[name]
    except KeyError:
        logger = logging.getLogger(name)
        loggers[name] = logger
    return logger

choose_logger = chooseLogger

class easyLogger(logging.Logger):

    def callHandlers(self, record, **kwargs):
        """
        Pass a record to all relevant handlers.

        Loop through all handlers for this logger and its parents in the
        logger hierarchy. If no handler was found, output a one-off error
        message to sys.stderr. Stop searching up the hierarchy whenever a
        logger with the "propagate" attribute set to zero is found - that
        will be the last logger whose handlers are called.

        Modified to pass through kwargs
        Modified to count and return actual emits.  (in place of None)

        """
        c = self
        used = found = 0
        while c:
            for hdlr in c.handlers:
                found = found + 1
                if record.levelno >= hdlr.level:
                    used += hdlr.handle(record, **kwargs)
            if not c.propagate:
                c = None    #break out
            else:
                c = c.parent

        # No handlers is a warning, but without a handler, we cannot really
        # emit it, nor can we use filterUnique to suppress the next such
        # call -- so we count emits in an attribute on the manager. 
        if not found and not self.manager.emittedNoHandlerWarning:
            sys.stderr.write("No handlers could be found for logger"
                             " \"%s\"\n" % self.name)
            self.manager.emittedNoHandlerWarning = 1
            
        return used

    def exception(self, msg, *args, **kwargs):
        """
        Convenience method for logging an ERROR with exception information.

        Modified to pass through additional keywords.

        """
        if 'exc_info' not in kwargs:
            kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)

    def findCaller(self):
        """
        Log a message from where?

        Ensure that easylog is not mistaken for the caller.

        Find the stack frame of the caller so that we can note the source
        file name and line number.
        
        """
        return findLogCaller()

    def getHandlers(self):
        return self.handlers
    
    def handle(self, record, **kwargs):
        """
        Call the handlers for the specified record.

        This method is used for unpickled records received from a socket, as
        well as those created locally. Logger-level filtering is applied.

        Overridden to pass through kwargs.

        """
        if (not self.disabled) and self.filter(record):
            self.callHandlers(record, **kwargs)

    def _log(self, level, msg, args, exc_info=None, **kwargs):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.

        Override to realize that easylog is not the actual caller, and
        to pass keyword arguments through.

        """
        fn, lno = self.findCaller()
        if exc_info and type(exc_info) != types.TupleType:
            exc_info = sys.exc_info()
        record = self.makeRecord(self.name, level,
                                 fn, lno,
                                 msg, args, exc_info)
        self.handle(record, **kwargs)

    def removeHandler(self, hdlr):
        """
        Remove the specified handler from this logger.

        This differs from base class in that it flushes first.
        It does not close, as base class made an explicit decision not to,
        in case the same handler is used by multiple loggers.  (Note that
        the duplicate usage may not even be within the easylog framework.)
        
        """
        if hdlr in self.handlers:
            hdlr.flush()
            self.handlers.remove(hdlr)

    def setHandlers(self, newHandlers=None, propagate=None,
                    new_handlers={}):
        """Set the handlers to (only) of newHandlers.

        propagate=True indicates that more general loggers should still
        be allowed to see the messages.  False indicates that this is a
        complete set, and None indicates no change.

        new_handlers is an alternative spelling of newHandlers.

        Add new handlers before removing old ones in case another thread
        emits log records in the middle of this operation.

        """
        if newHandlers is None:
            newHanders = new_handlers
        for newHandler in newHandlers:
            self.addHandler(newHandler)
        for oldHandler in self.handlers:
            if oldHandler not in newHandlers:
                self.removeHandler(oldHandler)
        if propagate is not None:
            self.propagate = propagate


logging.setLoggerClass(easyLogger)
    
def set_logger(name=None, level=None, handlers=None, propagate=None):
    """Set properties for the requested logger (default to the calling file).

    If the logger does not already exist, it will be created.  If it does,
    the attribute values will be changed as requested.  None leaves a value
    unchanged.  In particular, use propagate=False to shut off propagation.

    """

    logger = choose_logger(name)
    if name is not None:
        # If the caller specified a logger name, it applies to the whole
        # file (at least until they change it again).  This saves the user
        # from needing to keep a reference and use bound methods.
        f, ignored = findLogCaller()
        if f == unknown_file_name:
            f = "easylog"
        loggers[f] = logger

    # level = 0 is valid, but beware:  The logging package treats it specially.
    if level is not None:
        logger.setLevel(level)

    if handlers is not None:
        logger.setHandlers(handlers)

    if propagate is not None:
        logger.propagate = propagate
    elif not logger.getHandlers():
        # If there are no handlers here, propagate by default.
        logger.propagate = True

    logger.easylog_setup = True

    # The user does not need to keep any references, but they do have
    # the option, in case they want to alternate loggers for some
    # reason.
    return logger

# Maintain an API consistent with logging, but also with python
# style guides.
getLogger = setLogger = get_logger = set_logger

########################################################################
#
# Nothing is actually inherited from logging.Filter, and the only API
# is a method named filter which takes a record and returns True if
# the record is *not* thrown out by this filter.  (Think of it as "keepif"
# instead of "filter", but any filter may veto.)  We inherit in case
# someone has written code using isinstance.
#
########################################################################
class FilterUnique(logging.Filter):

    """Ensures that a message will only appear once.

    exact=False means to ignore parameters, such as *which* file could
    not be read.

    If minLevel or maxLevel are set, then messages outside that range
    will be ignored.  They may be repeated, and they will not prevent
    the appearance of the first message with an appropriate level.
    (min_level and max_level are alternative spellings, to support the
    python style guide, rather than the logging style.)

    hide is the dictionary of initially hidden messages.

    min_level and max_level are alternative spellings for minLevel
    and maxLevel, respectively.

    """
    
    def __init__(self,
                 minLevel = None, maxLevel=None,
                 exact=False,
                 hide=None,
                 min_level=None, max_level=None):
        self.min_level = minLevel or min_level
        self.max_level = maxLevel or max_level or self.min_level
        self.exact = exact
        self.hide = hide or {}

    def filter(self, record):
        "Return True unless this filter vetoes the record."""

        # Return True (OK) if this filter is not applicable.
        if self.min_level is not None and self.min_level > record.levelno:
            return True
        if self.max_level is not None and self.max_level < record.levelno:
            return True
        
        # Supress "duplicate" messages.
        if self.exact:
            key = record.getMessage()
        else:
            key = record.msg
        # Already seen?
        if key in self.hide:
            return False
        # This is the first time.  Make sure it is also the last time.
        # (Well, maybe unless it comes through with a different priority.)
        self.hide[key] = True
        return True
        

##########################################################################
#                                                                        #
# Examples (and default setup)                                           #
#                                                                        #
# Below here is sample complex usage, used for the defaults.             #
#                                                                        #
##########################################################################

class DefaultConsole(StreamHandler):
    """send Warnings on up to stderr.

    Supress messages less important than a Warning.

    Each Warning is sent only once.

    Each Error is sent once per detailed message.  (Example:  Failing to
    open a file would display only once, but failing to open a different file
    would still be reported.)

    Critical messages are always sent.

    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('level', WARNING)
        kwargs.setdefault('filters', (FilterUnique(WARNING),
                                      FilterUnique(ERROR, ERROR, exact=True)))
        kwargs.setdefault('format', BASIC_FORMAT)
        
        StreamHandler.__init__(self, *args, **kwargs)


class DefaultLogFile(RotatingFileHandler):
    """Log everything to (current directory).EasyLogA.*

    Rollover at the start of each run.
    Only keep 100K/file, to avoid resource exhaustion.
    Normally keep 7 runs ~= a week's worth.

    """
    def __init__(self, *args, **kwargs):

        # Defaults to logging in current working directory,
        kwargs.setdefault('filename', "EasyLogA")

        # An infinite loop can fill maxBytes * backupCount, so make it small
        kwargs.setdefault('maxBytes', 100000)
        kwargs.setdefault('backupCount', 7)

        kwargs.setdefault('format', EXTENDED_FORMAT)

        # 0 (==logging.NOTSET) gets special-cased to really be WARNING,
        # so DEBUG and INFO messages are discarded.
        # If the user has not specified a level, then we should log
        # everything they say to log, at least to the logfile.
        kwargs.setdefault('level', -1)
        
        RotatingFileHandler.__init__(self, *args, **kwargs)

        # Start a new logfile with each session.
        self.doRollover()


setLogger(name=None, level=-1, propagate=False,
          handlers=(DefaultConsole(), DefaultLogFile()))

# We use getLogger() because calls from within this file are not
# recognized as the "real" caller.
internal = getLogger('easylog')

internal.info("Logging Started (easylog %d.%d.%d %s patch %d)" %  __version__)

if leftovers:
    internal.debug("Unexpected symbols from logging package: %s", leftovers)
    
if phantoms:
    internal.warning("Overriding unexpected symbols from logging package: %s",
                     phantoms)
    
