// Versión final del 28 de diciembre de 2021
#include <Arduino.h>
#include "max6675.h"

#define MAXDO   4
#define MAXCS   5
#define MAXCLK  6

// initialize the Thermocouple
MAX6675 thermocouple(MAXCLK, MAXCS, MAXDO);
const int pinLED = 9;
const int pinT1 = 0;
const int heatPin1 = 3;

float Q1 = 0;
float P1 = 255; // Esto debe ser un valor comprendido entre 255 y 0. Es la potencia máxima.

const char sp = ' ';
const char nl = '\n';          // command terminator

bool control = false;

String version = "V0.3, DLF"; //termopar tipo k
char Buffer[64];
int buffer_index = 0;          // index for Buffer

bool newData = false;
String cmd;
double val;
double spT1 = 25;
double kc, ki, kd; // se modifica con setKc
unsigned long sampleTime = 1000; // Lo configuro en medio segundo.
double lastErr;
double output_pid;

double error;
double errorSum;
double errorI;
double errorD;
double Time;
double last_input; // Para evitar el derivative kick introducido en versión 0.2
unsigned long lastTime;
int n=10;

float outMax =100; // Límite de la variable de control para evitar el wind-up
float outMin=0; // Límite de la variable de control para evitar el wind-up
bool inAuto = false;


#define AUTOMATIC 1
#define MANUAL 0



void setup() {
    Serial.begin(115200);
    Time = millis();
    pinMode(pinLED, OUTPUT);
    Serial.flush();
}

float getTemperature(int pin){
    float degC = 0.0;
    int n = 10;
    for (int i=0; i<n; i++){
        //degC += analogRead(pin);
        degC += thermocouple.readCelsius();
    }
    float lectura = degC/float(n);
    //float temp= 120.0 /1024 * lectura ;
    //float voltaje = 3.3 /1024 * lectura ; // Atencion aqui
    //float temp = voltaje * 100 -50;

    return lectura;

}

float setHeater1(float valQ1){
    Q1 = max(outMin, min(valQ1,outMax));
    analogWrite(heatPin1,  (Q1 * P1/100.) );
}

float setSetPoint(float valT){
    spT1 = max(20, min(valT,200));
}

float setKcVal(float valKC){
    kc = valKC;
}

float setKiVal(float valKI){
    // Se calcula el valor de KI multiplicado ya por el tiempo porque se pone que controle regular
    if (valKI == 0.0) {
        ki = 0.0;
        errorI = 0;
    }else{
        ki = (kc/valKI) * sampleTime/1000;
    }

}

float setKdVal(float valKd){
    kd = kc * valKd / (sampleTime/1000.0);
}

void readCommand() {
    while (Serial && (Serial.available() > 0) && (newData == false)) {
        int byte = Serial.read();
        if ((byte != '\r') && (byte != nl) && (buffer_index < 64)) {
            Buffer[buffer_index] = byte;
            buffer_index++;
        }
        else {
            newData = true;
        }
    }
}

void parseCommand(void) {
    if (newData) {
        String read_ = String(Buffer);
        // separate command from associated data
        int idx = read_.indexOf(sp);
        cmd = read_.substring(0, idx);
        cmd.trim();
        cmd.toUpperCase();

        // extract data. toFloat() returns 0 on error
        String data = read_.substring(idx + 1);
        data.trim();
        val = data.toFloat();

        // reset parameter for next command
        memset(Buffer, 0, sizeof(Buffer));
        buffer_index = 0;
        newData = false;
    }
}

void sendResponse(String msg) {
    Serial.println(msg);
}

void sendFloatResponse(float val) {
    Serial.println(String(val, 3));
}

void sendControlResponse(float T1){

    Serial.print("{");
    Serial.print("\"Q1\" : " + String(Q1, 3) + "," );
    Serial.print(" \"T1\" : " + String(T1,3) + "," );
    Serial.print(" \"spT1\" : " + String(spT1,3) + "," );
    Serial.print(" \"kc\" : " + String(kc,3) + "," );
    Serial.print(" \"ki\" : " + String(ki,3) + "," );
    Serial.print(" \"kd\" : " + String(kd,3) + "," );
    Serial.print(" \"error\" : " + String(error,3) + "," );
    Serial.print(" \"errorI\" : " + String(errorI,3) + "," );
    Serial.print(" \"errorD\" : " + String(errorD,3)+ ",");
    Serial.print(" \"Modo\" : " + String(inAuto));
    Serial.println("}");
}

void controlPID(){

    if (!inAuto) return;
    unsigned long now;
    now = millis();
    unsigned long timeChange;
    timeChange= (now - lastTime);
    if (timeChange >= sampleTime){

        float input = getTemperature(pinT1);

        error = -input + spT1;
         // Determina si hay que ejecutar el PID o retornar de la función. if(timeChange>=SampleTime)
        // Calcula todas las variables de error.
        errorSum += error;
        errorI += (ki * error);

        //if (errorI > outMax) errorI = outMax;
        //else if (errorI< outMin) errorI = outMin;
        double dInput = (input - last_input);
        errorD = (error - lastErr);

        float P = kc  * error;
        float I = errorI;
        float D = -kd * dInput;

        output_pid = P + I + D;

        if (output_pid > outMax){
            errorI -= (ki * error);
            output_pid = outMax;

        }else if (output_pid< outMin){
            errorI -= (ki * error);
            output_pid = outMin;

        }

        /*if (output_pid>= outMax || output_pid <= outMin ){
            // Anti windup, si el control está saturado no incremento el error integral
            errorI -= ki * errorI;
        }*/
        // Calculamos la función de salida del PID.
        // resto la variación del dInput para evitar los saltos de la derivada V0.2
        // Guardamos el valor de algunas variables para el próximo ciclo de cálculo.
        setHeater1(output_pid);
        last_input = input;
        lastErr = error;
        lastTime = now;
    }
}

void setSampleTime(unsigned long newSampleTime){
    if (newSampleTime>0){
        double ratio = (double)newSampleTime / (double)sampleTime;
        ki *= ratio;
        kd /= ratio;
        sampleTime = newSampleTime;
    }
}

void initialize(){
    /*Inicializa tras el cambio de modo*/
    last_input = getTemperature(pinT1);
    errorI = output_pid;
    if (errorI > outMax) errorI = outMax;
    else if (errorI<outMin) errorI = outMin;
}

void setMode(float val){
    if (int(val) == AUTOMATIC){
        inAuto = true;
    }else{
        inAuto =  false;
    }
    initialize();

}



void setMaxout(float val){
    outMax = min(val, 100);
}

void setMinout(float val){
   outMin = max(val, 0);
}

void accion(void){
    if (cmd == "A"){
        setHeater1(0);
        sendResponse("Start");
        control = true;
        error =0;
        errorI =0;
        errorD =0;
    }

    else if(cmd=="T1"){
        float T1 = getTemperature(pinT1);
        Serial.println(T1);
    }
    else if (cmd == "Q1") {
        setHeater1(val);
    }
    else if (cmd == "getQ1") {
        sendFloatResponse(Q1);
    }
    else if (cmd == "T1S"){
        setSetPoint(val);
    }
    else if (cmd == "getT1S"){
        sendFloatResponse(spT1);
    }
    else if (cmd == "KCS"){
        setKcVal(val);
    }
    else if (cmd == "getKCS"){
        sendFloatResponse(kc);
    }
    else if (cmd == "KIS"){
        setKiVal(val);
    }
    else if (cmd == "getKIS"){
        sendFloatResponse(ki);
    }
    else if (cmd == "KDS"){
        setKdVal(val);
    }
    else if (cmd == "getKDS"){
        sendFloatResponse(kd);
    }

    else if (cmd == "setTimeSample"){
        setSampleTime(val);
    }

    else if (cmd == "ymax"){
        setMaxout(val);
    }
    else if (cmd == "ymax"){
        setMinout(val);
    }
    else if (cmd == "E"){
        setMode(val);
    }
    else if (cmd=="B"){
        if (control){
            sendControlResponse(getTemperature(pinT1));
        }
        else{
            Serial.println("No controla en espera");
        }
    }
    else if (cmd == "X"){
        control = false;
        sendResponse("stop");
        setHeater1(0);
        setSetPoint(25);

    }
    else if (cmd == "VER"){
        sendResponse(version);

    }
    Serial.flush();
    cmd = "";
}

void loop() {
  if (Serial.available()>0) {
    myserialEvent();
  }
  if (control) {
    controlPID();
  }
}
void myserialEvent(){ // Versión 0.3 quito el Serial event.
  readCommand();
  parseCommand();
  accion();
}