from pathlib import Path
from PySide6 import QtCore


def absPath(file):
    return str(Path(__file__).parent.absolute() / file)

def diaISO():
    dia = QtCore.QDate.currentDate()
    return dia.toString(QtCore.Qt.ISODate)

def horaISO():
    hora = QtCore.QTime.currentTime()
    return hora.toString(QtCore.Qt.ISODateWithMs)

