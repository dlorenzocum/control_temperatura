# pyside6-uic form.ui -o ui_form.py
# designer.exepip install pipenv
import json
import sys

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QDialog, QMessageBox, QSplashScreen
from PySide6 import QtCore
from PySide6.QtGui import QPixmap, Qt

from GUI_v2.ui_mainwindow import Ui_MainWindow
import time
from conexion_arduino import Arduino
from helpers import absPath, horaISO, diaISO
from GUI_v2.ui_dialog_informacion import Ui_Dialog
import GUI_v2.ui_about as about_w
import GUI_v2.ui_set_temp as st_w
import GUI_v2.ui_set_control as sc_w
import GUI_v2.ui_set_limite_valvula as sl_w
import GUI_v2.ui_graficos as gr_w
import GUI_v2.ui_no_conexion as noc_w

import GUI_v2.ui_dialog_conect_arduino as con_w

import pyqtgraph as pg
import os
import errno
import pandas as pd
import json as js



class WorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    results = QtCore.Signal(object)

class Worker(QtCore.QRunnable):
    def __init__(self, fn): # Aquí añado la función que quiero ejecutar como fn
        super().__init__()
        self.signals = WorkerSignals()
        self.fn = fn #Función que quiero ejecutar

    @QtCore.Slot()
    def run(self):
        result = self.fn() # Ejecuto la función en results
        self.signals.results.emit(result)
        self.signals.finished.emit()


        #self.signals.start_control.emit()

class InfoArduino(QWidget, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Dialog_set_temp (QDialog, st_w.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Dialog_set_control(QDialog, sc_w.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Dialog_set_limits(QDialog, sl_w.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Dialog_about(QDialog, about_w.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Dialog_graficos(QDialog, gr_w.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Diagl_conectar(QDialog, con_w.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class Diagl_no_conexion(QDialog, noc_w.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

class UI(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.threadpool = QtCore.QThreadPool() # Hilos de ejecución
        print("Multithreading con un máximo de %d hilos" % self.threadpool.maxThreadCount())


        self.setWindowTitle("Control de temperatura")

        self.datos1 =  [{"nombre": "T Actual (ºC)", "valores": [], "color": "r"},
                        {"nombre": "Set point T (ºC)", "valores": [], "color": "w"}]

        self.datos2 =  [{"nombre": "Acción de control", "valores": [], "color": "r"}]

        self.sondas = [
            {"nombre": "Sonda 1", "valores": [], "color": "r", "simbolo": "o"},
            {"nombre": "Sonda 2", "valores": [], "color": "b", "simbolo": "+"},
            {"nombre": "Sonda 3", "valores": [], "color": "g", "simbolo": "star"},
        ]
        self.graficar = False
        #self.mode = 0 # modo de operación del controlador, manual 0 automático 1

        self.temperaturaSET = 20 # es el setpoint de temperatura

        self.openValve = 0 # es la apertura de válvula

        self.hw = Arduino()  # Creo la clase arduino pero no lo conecto.

        self.df_plot = pd.DataFrame(columns=['Q1', 'T1', 'spT1', 'kc', 'ki', 'kd', 'error', 'errorI', 'errorD', 'Modo',
                                             'time'])
        self.df_datos_sesion = pd.DataFrame(columns=['Q1', 'T1', 'spT1', 'kc', 'ki', 'kd', 'error', 'errorI', 'errorD', 'Modo',
                                             'time'])
        self.datos_export = {}

        self.data = {}

        self.datos_sesion=[]
        self.buffer = ""
        # win_ hago referencia a las pantallas de diálogo

        # Creo la pantalla de información del arduino

        self.win_infoarduino = InfoArduino()  # Creo la pantalla de información
        self.con_informacion.clicked.connect(self._win_info_arduino)  # activo la pantalla de información

        self.horaConexion = None

        self.con_about.clicked.connect(self._win_about)

        # creo la pantalla de conexión del arduino
        self.win_conectar = Diagl_conectar()
        self.toolButton.clicked.connect(self._conectar_win)


        #self.conectar_arduino()

        #pantalla principal

        self.doubleSpinBox_valve.setValue(self.openValve)
        self.doubleSpinBox_temp.setValue(self.temperaturaSET)
        self.doubleSpinBox_valve.valueChanged.connect(self.set_valve)
        self.doubleSpinBox_temp.valueChanged.connect(self.set_temperatura)


        #Pantalla de controlador:
        self.win_setC = Dialog_set_control()
        self.set_c.clicked.connect(self._win_set_control)

        # Creo la pantalla de los límites de apertura de la válvula
        self.win_setLimits = Dialog_set_limits()
        self.win_setC.pushButton.clicked.connect(self._win_set_limites)

        #Creo la pantalla de graficos
        self.win_graficos = Dialog_graficos()
        self.construirGrafico()
        self.toolButton_graficos.clicked.connect(self._win_graficos)

        self.win_graficos.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        # Pantalla de no conexión

        self.win_no_conexion = Diagl_no_conexion()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.verificar_conexion_arduino)
        self.timer.start(5000)  # 5000 ms = 5 segundos

    def _win_info_arduino(self):
        self.win_infoarduino.show()

    def _win_about(self):
        win = Dialog_about()
        win.exec()

    def _win_set_control(self):

        self.win_setC.show()

        self.win_setC.doubleSpinBox_setT.setValue(self.temperaturaSET)
        self.win_setC.doubleSpinBox_valve.setValue(self.openValve)

        self.win_setC.manual_mode.clicked.connect(self.set_manual) #cambiar a modo manuak
        self.win_setC.auto_mode.clicked.connect(self.set_auto) # cambiar a modo automático
        self.win_setC.toolButton_stopcontrol.clicked.connect(self.stopControl)
        self.win_setC.pushButton_.clicked.connect(self._setPID)

        respuesta = self.win_setC.exec()

        if respuesta:
            self._setPID()

    def _setPID(self):
        if self.mode == 1:
            spT = self.win_setC.doubleSpinBox_setT.value()
            kc = self.win_setC.doubleSpinBox_kc.value()
            ki = self.win_setC.doubleSpinBox_ki.value()
            kd = self.win_setC.doubleSpinBox_kd.value()
            self.doubleSpinBox_temp.setValue(spT)
            self.hw.setControl_PID(kc, ki, kd)
        else:
            oValve = self.win_setC.doubleSpinBox_valve.value()
            self.openValve = oValve
            self.doubleSpinBox_valve.setValue(oValve)

    def set_valve(self):
        """Envía la aperutra de válvula en modo manual al arduino"""
        self.openValve = self.doubleSpinBox_valve.value()
        print(self.openValve)
        if self.hw.connect:
            self.hw.setQ1(self.openValve)

    def set_temperatura(self):
        """Envía el set de temperatua en modo automático al arduino"""
        self.temperaturaSET = self.doubleSpinBox_temp.value()
        if self.hw.connect:
            self.hw.setSp(self.temperaturaSET)

    def set_manual(self):
        self.mode = 0
        self.win_setC.doubleSpinBox_kc.setEnabled(False)
        self.win_setC.doubleSpinBox_kd.setEnabled(False)
        self.win_setC.doubleSpinBox_ki.setEnabled(False)
        self.win_setC.doubleSpinBox_setT.setEnabled(False)
        self.win_setC.doubleSpinBox_valve.setEnabled(True)
        self.doubleSpinBox_temp.setEnabled(False)
        self.doubleSpinBox_valve.setEnabled(True)
        self.win_graficos.label_4.setPixmap(QPixmap(u":/iconos/manual_peq.png"))
        self.label_7.setPixmap(QPixmap(u":/iconos/manual_peq.png"))
        if self.hw.connect:
            self.hw.send("E " + str(self.mode))
        else:
            self.no_conexion()

    def set_auto(self):
        self.mode=1
        self.win_setC.doubleSpinBox_kc.setEnabled(True)
        self.win_setC.doubleSpinBox_kd.setEnabled(True)
        self.win_setC.doubleSpinBox_ki.setEnabled(True)
        self.win_setC.doubleSpinBox_setT.setEnabled(True)
        self.win_setC.doubleSpinBox_valve.setEnabled(False)
        self.doubleSpinBox_temp.setEnabled(True)
        self.doubleSpinBox_valve.setEnabled(False)

        if self.hw.connect:
            self.hw.send("E " + str(self.mode))
            self.win_graficos.label_4.setPixmap(QPixmap(u":/iconos/auto_peq.png"))
            self.label_7.setPixmap(QPixmap(u":/iconos/auto_peq.png"))
        else:
            self.no_conexion()

    def _win_set_limites(self):

        if self.hw.connect:
            self.win_setLimits.show()
            respuesta = self.win_setC.exec()
            if respuesta:
                ymax = self.win_setLimits.doubleSpinBox_ymax.value()
                ymin = self.win_setLimits.doubleSpinBox_ymin.value()
            self.hw.setlimites(ymax, ymin)
        else:
            self.no_conexion()

    def _win_graficos(self):
        self.win_graficos.show()
        self.win_graficos.toolButton_play.clicked.connect(self._graficar_star)
        self.win_graficos.toolButton_pause.clicked.connect(self._graficar_pause)
        self.win_graficos.toolButton_export.clicked.connect(self._exportar_datos)

    def _conectar_win(self):
        self.win_conectar.show()
        self.win_conectar.toolButton_2.clicked.connect(self.conectar_arduino)
        self.win_conectar.toolButton_3.clicked.connect(self.stopControl)

    def construirGrafico(self):
        # configuración base
        self.win_graficos.widget.addLegend()

        self.graficos1 = []
        for linea in self.datos1:
            plot = self.win_graficos.widget.plot(linea["valores"], name=linea["nombre"],
                                         pen=pg.mkPen(linea["color"], width=3))
            self.graficos1.append(plot)
            # estilos del gráfico
        #self.win_graficos.widget.setBackground("w")
        self.win_graficos.widget.showGrid(x=True, y=True)
        self.win_graficos.widget.setYRange(-20, 30)  # self.widget.setXRange(0, 10)
        self.win_graficos.widget.setTitle("Monitor de temperaturas", size="24px")

        styles = {"color": "#FFFFFF", "font-size": "20px"}
        self.win_graficos.widget.setLabel("left", "Temperaturas (ºC)", **styles)
        self.win_graficos.widget.setLabel("bottom", "tiempo (s)", **styles)

        self.win_graficos.widget_2.addLegend()

        self.graficos2 = []

        for linea in self.datos2:
            plot = self.win_graficos.widget_2.plot(linea["valores"], name=linea["nombre"],
                                         pen=pg.mkPen(linea["color"], width=3))
            self.graficos2.append(plot)

        #self.win_graficos.widget_2.setBackground("w")
        self.win_graficos.widget_2.showGrid(x=True, y=True)
        self.win_graficos.widget_2.setYRange(-20, 30)  # self.widget.setXRange(0, 10)
        self.win_graficos.widget_2.setTitle("Acción de control", size="24px")

        styles = {"color": "#FFFFFF", "font-size": "20px"}
        self.win_graficos.widget_2.setLabel("left", "Acción de control (%)", **styles)
        self.win_graficos.widget_2.setLabel("bottom", "tiempo (s)", **styles)

    def setstatusarduino(self):
        if self.hw.port is None:
            self.win_conectar.status_label.setText("Controlador desenchufado")
        else:
            self.win_conectar.status_label.setText("Conectado")
            self.conectar_arduino()
            self.horaConexion = horaISO().replace(':', '-')
            # Envia la información a la pantalla de información.
            self.win_infoarduino.control_info.setText(self.hw.arduino)
            self.win_infoarduino.port_info.setText(self.hw.port)
            self.win_infoarduino.ver_info.setText(self.hw.version)
            self.win_infoarduino.time_info.setText(self.horaConexion)  # indica el tiempo de conexión

    def conectar_arduino(self):
        """Conecto arduini si no está conectado"""
        if (self.hw.connect):
            self.win_conectar.status_label.setText("Arduino ya conectado")
        else:
            self.win_conectar.status_label.setText("Conexión fallida: Arduino no encontrado")
            self.hw.reconectar()
            self.hw.conectar_arduino()
            self.set_manual() # La primera vez que conecto es en modo manual.

            if (self.hw.connect):
                self.setstatusarduino()
                self.hw.start()
                self.datosConcurrentes()
                self.win_conectar.status_label.setText("Arduino ya conectado")
                self.label_5.setPixmap(QPixmap(u":/iconos/green_b_peq.png"))
                self.win_graficos.label_6.setPixmap(QPixmap(u":/iconos/green_b_peq.png"))

    def datosConcurrentes(self):
        """Número de acciones en paralelo"""
        worker = Worker(self.getDatos)
        self.threadpool.start(worker)
    
    def gestionarDatos(self,data):
        self.buffer += data
        try:
            while True:
                start = self.buffer.find("{")
                end = self.buffer.find("}", start) + 1
                if start == -1 or end == 0:
                    break
                json_data = self.buffer[start:end]
                self.buffer = self.buffer[end:]
                datos_arduino = json.loads(json_data)
                datos_arduino['time'] = horaISO()
                new_data_series = pd.Series(datos_arduino)
                if self.graficar:
                    self.plot(new_data_series)
                self.df_datos_sesion = pd.concat([self.df_datos_sesion, new_data_series.to_frame().T], ignore_index=True)
                self.showData(datos_arduino)
                self.df_datos_sesion.to_csv(absPath(diaISO()) + '/' + diaISO() +'_'+ self.horaConexion+'_'+'datos.csv', index=False)
        except json.JSONDecodeError as e:
            print(f"Error de JSON: {e}")
    
    def verificar_conexion_arduino(self):
        
        if self.hw.verificar_conexion():
            print('Verificando conexión: ok')
        else:
            print("Arduino desconectado. Intentando reconectar...")
            self.hw.reconectar()
            self.hw.connect = False
            self.label_5.setPixmap(QPixmap(u":/iconos/red_b_peq.png"))
            self.win_graficos.label_6.setPixmap(QPixmap(u":/iconos/red_b_peq.png"))
            self.win_conectar.status_label.setText("Arduino desenchufado")
                  
    def getDatos(self):
        """Pide los datos a Arduino de manera constante cada 1 s"""
        #self.hw.connect = True
        while self.hw.connect:
            self.data = self.hw.getData()
            time.sleep(1)
            self.gestionarDatos(self.data)
                       
    def plotDatos(self):
        if self.graficar:
            self.datos_export =pd.DataFrame(self.data, index = [1])
            self.plot(self.data)
            self.df_plot=pd.concat([self.df_plot, self.datos_export])

    def _graficar_pause(self):
        self.win_graficos.label_8.setPixmap(QPixmap(u":/iconos/red_b_peq.png"))
        self.graficar = False

    def _graficar_star(self):
        self.graficar = True
        self.win_graficos.label_8.setPixmap(QPixmap(u":/iconos/green_b_peq.png"))
    
    def _exportar_datos(self):
        self.df_plot.to_csv(absPath('dat1.csv'))

    def plot(self, data):
        self.datos1[0]["valores"].append(data['T1'])
        self.graficos1[0].setData(self.datos1[0]["valores"])
        self.datos1[1]["valores"].append(data['spT1'])
        self.graficos1[1].setData(self.datos1[1]["valores"])
        self.datos2[0]["valores"].append(data['Q1'])
        self.graficos2[0].setData(self.datos2[0]["valores"])

    def showData(self, data):
        self.lcdNumber.display(data['T1'])
        self.win_setC.lcdNumber.display(data['T1'])
        self.lcdNumber_valve.display(data['Q1'])

        self.win_graficos.lcdNumber_temp.display(data['T1'])
        self.win_graficos.lcdNumber_valve.display(data['Q1'])

        #.self.plotDatos()

    def closeEvent(self, event):
        close = QMessageBox.question(self, "QUIT", "¿Seguro qué deseas cerrar la sesión?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if close == QMessageBox.Yes:
            if self.hw.connect:
                self.stopControl()

            self.win_conectar.close()
            self.win_graficos.close()
            self.win_infoarduino.close()
            self.win_setC.close()
            self.con_about.close()
            self.win_setLimits.close()
            event.accept()
        else:
            event.ignore()
    
    def stopControl(self):
        if self.hw.connect:
            self.hw.stop()
            self.hw.connect = False
            self.win_conectar.status_label.setText("Control: OFF")
            self.hw.disconnect()
        else:
            self.no_conexion()

    def no_conexion(self):
        self.win_no_conexion.show()

        
if __name__ == "__main__":
    try:
        os.mkdir(absPath(diaISO()))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    app = QApplication(sys.argv)
    widget = UI()
    widget.show()
    sys.exit(app.exec())

