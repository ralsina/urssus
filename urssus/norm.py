# -*- coding: utf8 -*-

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

import unicodedata

def _norm_car(car):
    # si es una letra simple, no hace falta normalización, nos fijamos
    # primero porque es más rápido
    if ord(car) < 128:
        return car

    # descomponemos y vemos en qué caso estamos
    decomp = unicodedata.decomposition(car)
    if decomp == "":
        # no tiene
        res = car
    elif decomp.startswith("<compat>"):
        # compatibilidad
        utiles = [x for x in decomp.split()][1:]
        res = u"".join(unichr(int(x, 16)) for x in utiles)
    else:
        # nos quedamos con el primero
        prim = decomp.split()[0]
        res = unichr(int(prim, 16))

    # guardamos en el caché y volvemos
    return res

def normalizar(palabra):
    return u"".join(_norm_car(c) for c in palabra)
