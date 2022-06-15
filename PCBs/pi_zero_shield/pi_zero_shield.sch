EESchema Schematic File Version 4
EELAYER 30 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title ""
Date ""
Rev ""
Comp ""
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L Device:Buzzer BZ1
U 1 1 61ED03BA
P 8400 4050
F 0 "BZ1" V 8451 3863 50  0000 R CNN
F 1 "Buzzer" V 8360 3863 50  0000 R CNN
F 2 "" V 8375 4150 50  0001 C CNN
F 3 "~" V 8375 4150 50  0001 C CNN
	1    8400 4050
	-1   0    0    1   
$EndComp
$Comp
L Connector_Generic:Conn_01x10 J3
U 1 1 61ED0E16
P 4200 2250
F 0 "J3" H 4280 2242 50  0000 L CNN
F 1 "Conn_01x10" H 4280 2151 50  0000 L CNN
F 2 "" H 4200 2250 50  0001 C CNN
F 3 "~" H 4200 2250 50  0001 C CNN
	1    4200 2250
	0    -1   -1   0   
$EndComp
$Comp
L Connector_Generic:Conn_01x08 J1
U 1 1 61ED276A
P 4300 5850
F 0 "J1" H 4218 5225 50  0000 C CNN
F 1 "Conn_01x08" H 4218 5316 50  0000 C CNN
F 2 "" H 4300 5850 50  0001 C CNN
F 3 "~" H 4300 5850 50  0001 C CNN
	1    4300 5850
	0    1    1    0   
$EndComp
$Comp
L Connector_Generic:Conn_02x20_Odd_Even J2
U 1 1 61EC6EB2
P 5650 3900
F 0 "J2" V 5654 2813 50  0000 R CNN
F 1 "Conn_02x20_Odd_Even" V 5745 2813 50  0000 R CNN
F 2 "custom:Pi_PinSocket_2x20" H 5650 3900 50  0001 C CNN
F 3 "~" H 5650 3900 50  0001 C CNN
	1    5650 3900
	1    0    0    -1  
$EndComp
$EndSCHEMATC
