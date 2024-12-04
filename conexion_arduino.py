import serial
import time
from serial.tools import list_ports
import json
from helpers import absPath
import collections


class Arduino:
    """
    Clase Arduino:
    Constructor:
    * Atributos de la clase Arduino:
        connect: representa si el la placa de arduino está concetada (True) o no. La
        baud:
        arduino y puerto: estos atributos se obtienen dende la función find_arduino()
        self.version: devuelve la versión del programa cargado.
        si no hay puerte concetado devuelve el error arduino no encontrado.
    * Métodos de instancia:
        concetar_arduino()
    """
    def __init__(self):
        self.connect = False
        self.baud = 115200
        self.arduino, self.port= self.find_arduino()
        self.version = None
        if self.port is None:
            self.arduino_no_encontrado()
        
        self.hw = None
            
    def find_arduino(self, port=''):
        arduinos = [('USB VID:PID=16D0:0613', 'Arduino Uno'),
                ('USB VID:PID=1A86:7523', 'NHduino'),
                ('USB VID:PID=2341:8036', 'Arduino Leonardo'),
                ('USB VID:PID=2A03', 'Arduino.org device'),
                ('USB VID:PID', 'unknown device'),
                ('USB VID:PID=2341:0058', 'Arduino NANO every')
                ]
    
        """Locates Arduino and returns port and device. Si el arduno está concetado devuelve el 
        tipo de arduino y el pueto al que está concetado"""
        
        comports = [tuple for tuple in list_ports.comports() if port in tuple[0]]
        for port, desc, hwid in comports:
            for identifier, arduino in arduinos:
                if hwid.startswith(identifier):
                    return arduino, port
        return None, None
        
    def conectar_arduino(self):
        """Hardware connect"""
        try:
            self.hw = serial.Serial(self.port, self.baud, timeout=0.5) # Crea una istnacia de la clase Serial
            self.hw.reset_output_buffer() #Flush input buffer, discarding all its contents.
            time.sleep(2) # Espera 2 segundos para que conecte
            self.connect = True
            self.version = self.getVersion()
        except Exception as error:
            self.conexionfallida()
        else:
            self.conexioncorrecta()

    def reconectar(self):
        """Este método busca de nuevo el puerto y el arduino concetados"""
        if self.port is None:
            self.arduino, self.port = self.find_arduino()
            if self.port is None:
                self.arduino_no_encontrado()


    def disconnect(self):
        """Desconecta el arduino"""
        self.hw.close()
        self.connect = False
    
    def verificar_conexion(self):
        """Verifica si el Arduino sigue conectado."""
        if self.hw is None:
            self.arduino_no_encontrado()
            return False
        try:
            self.hw.in_waiting  # Verifica si la conexión sigue activa
            return True
        except (OSError, serial.SerialException):
                self.connect = False
                self.arduino_no_encontrado()
                return False
    
    def getPort(self):
        return self.port

    def arduino_no_encontrado(self):
        print("Arduino no encontrado")

    def conexioncorrecta(self):
        print("Conexión correcta")

    def conexionfallida(self):
        print("Conexión fallida")

    def send(self, msg):
        """Envía acción al Serial del arduino.
        Utiliza el métdo de la clase Serial que es write()"""
        self.hw.write((msg + '\n').encode('utf-8'))
        time.sleep(0.002)

    def recive(self):
        """Recibe un dato del serial del Arduino"""
        data = self.hw.readline().decode('utf-8').replace('\r\n', '')
        return data
  

    def getVersion(self):
        self.send("VER")
        data = self.recive()
        print("-----Arduino connected with V: ", data, "-------")
        return data

    def getData(self):
        self.send("B")
        data = self.recive()
        #j_data = json.loads(data)
        return data

    def getT1(self):
        self.send("T1")
        data = self.recive()
        return data

    def getT1S(self):
        self.send("getT1S")
        data = self.recive()
        return data

    def start(self):
        self.send("A")
        data = self.recive()
        return data

    def close(self):
        """Shut down control device and close serial connection."""
        self.send("X")
        data = self.recive()
        print('Arduino disconnected successfully.')
        self.connect = False
        return data

    def stop(self):
        """Shut down control device and close serial connection."""
        self.send("X")
        data = self.recive()
        return data

    def setControl_PID(self, kc, KI, KD):
        self.send("KCS " + str(kc))
        self.send("KIS " + str(KI))
        self.send("KDS " + str(KD))
        data = self.recive()
        return data

    def setKc(self, kc):
        self.send("KCS " + str(kc))

    def setKd(self, KD):
        self.send("KDS " + str(KD))

    def setKi(self, KI):
        self.send("KIS " + str(KI))

    def setSp(self, TSP):
        self.send("T "+ str(TSP))

    def setQ1(self, Q1):
        self.send("Q1 " + str(Q1))

    def setSampleTime(self, sampleTime):
        self.send("setTimeSample " + str(sampleTime))

    def setlimites(self, ymax, ymin):
        self.send("ymax " + str(ymax))
        self.send("ymin " + str(ymin))


def prueba():
    hw = Arduino()
    hw.conectar_arduino()
    data = []
    rawString_s = hw.start()

    print(rawString_s)

    rawString_s = hw.getT1()
    print(rawString_s)

    rawString_s = hw.getData()
    print(rawString_s)

    hw.setSp(100)

    rawString_s = hw.getData()
    print(rawString_s)

    i = 0
    c = True
    while c:
        rawString_s = hw.getData()
        i = i + 1
        if i == 5:
            hw.setSp(60)
            hw.setQ1(50)
        print(i, rawString_s, rawString_s["Q1"])

        if i == 30:
            hw.stop()
            c = False
        data.append(rawString_s)

    rawString_s = hw.getT1()
    print(rawString_s)



    with open(absPath("datos.json"), "w") as fichero:
        json.dump(data, fichero)

    with open(absPath("datos.json")) as fichero:
        datos = json.load(fichero)
        for dato in datos:
            print(dato['Q1'], dato['T1'], dato['spT1'])

    rawString_s = hw.close()
    print(rawString_s)
    print(hw.port)

    # rawString_s = hw.stopControl(hw)
    # rawString_s = hw.stopControl(hw)
    # print(rawString_s)

    # if (rawString_s.find("{") >= 0 and rawString_s.find("}") >= 0): #busco que esté el cierre y la apertura del json
    # rawString_j = json.loads(rawString_s)
    # print(rawString_j)
    # print(type(rawString_j))
    # else:
    # print("Error json perdido")
    # hw.close()

#prueba()
