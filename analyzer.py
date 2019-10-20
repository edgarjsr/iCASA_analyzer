# Script para analisis de representaciones persistentes (xml) generadas
# por el simulador de casa inteligente iCasa
#
# Edgar Silva R., 11-10968
#

#################################
# Imports                       #
#################################

# Manejo de xml
import xml.etree.ElementTree as ET

# Manejo herramientas del sistema
import sys

# Manejo de tiempo
import datetime
import time

# Funcion reduce
from functools import reduce

# Aniadir en este bloque

##################################
# Definicion de constantes AGGIR #
##################################

# NOTA: Las constantes tienen dos valores posibles de
# acuerdo al nivel de dependencia del sujeto, asi:

# True: la actividad se completa satisfactoriamente
# Flase: la actividad no es completada

# Diccionario de constantes AGGIR
AGGIR_CONST = {
	'COHERENCE': True,
	'LOCATION': True,
	'TOILETING': True,
	'DRESSING': True,
	'ALIMENTATION': True,
	'ELIMINATION': True,
	'TRANSFERS': True,
	'IN_MOVEMENTS': True,
	'OUT_MOVEMENTS': True,
	'DIST_COMMUNICATION': True,
	'MANAGEMENT': True,
	'COOKING': True,
	'HOUSEKEEPING': True,
	'TRANSPORTATION': True,
	'PURCHASES': True,
	'MEDICAL_TREATMENT': True,
	'LEISURE_ACTS': True,
}
#################################
# Constantes varias             #
#################################

# Maximo tiempo encendido de una luz (10 horas)
MAX_TIME_LIGHT_ON = datetime.timedelta(hours = 10)

# Maximo tiempo encendido de una heater/cooler
MAX_TIME_HEAT_COOL_ON = datetime.timedelta(hours = 12)

# Maxima concentracion de CO2 en ug/cub m, exposicion prolongada
MAX_CO2_CONCENTRATION = 9000

# Maxima concentracion de CO en ug/cub m, exposicion prolongada
MAX_CO_CONCENTRATION = 40

# Temperatura minima aceptable para activar heater (en kelvin)
# 16 celsius
MIN_TEMPERATURE = 289.15

# Temperatura minima aceptable para activar cooler (en kelvin)
# 30 celsius
MAX_TEMPERATURE = 303.15

# Tiempo minimo para ir a dormir
MIN_SLEEPING_TIME = datetime.time(20, 0, 0)

# Dia
DAYTIME_MIN = datetime.time(6, 0, 0)
DAYTIME_MAX = datetime.time(19, 59, 59)

# Noche
NIGHTTIME_MIN = datetime.time(20, 0, 0)
NIGHTTIME_MAX = datetime.time(5, 59, 59)

# Tiempo maximo consecutivo a estar de dia en bedroom
MAX_STILL_TIME_BEDROOM = datetime.timedelta(hours=4)

# Tiempo maximo consecutivo a estar dentro de la cocina
MAX_STILL_TIME_KITCHEN = datetime.timedelta(hours=3)

# Tiempo maximo consecutivo a estar dentro del banio
MAX_STILL_TIME_BATHROOM = datetime.timedelta(hours=2)

# Tiempo maximo consecutivo a estar en la sala
MAX_STILL_TIME_LIVINGROOM = datetime.timedelta(hours=5)

# Tiempo maximo consecutivo a estar en un pasillo
MAX_STILL_TIME_HALLWAY = datetime.timedelta(hours=1)

# Tiempo ideal para miccion
IDEAL_TIME_BW_MICTURITION = datetime.timedelta(hours=4)

# Veces de ida al banio promedio en un dia
AVERAGE_MICTURITION_FREQ = 6

# Tiempo prudencial para mantener la puerta principal abierta
MAX_MAIN_DOOR_OPEN_TIME = datetime.timedelta(minutes=30)

# Cantidad maxima de tiempo a estar fuera de la cocina mientras se prepara algo
MAX_TIME_OUT_COOKING = datetime.timedelta(minutes=45)

#################################
# Funciones utiles              #
#################################

# Funcion varsInList
# Retorna true si el key 'key' esta presente en algun elemento
# de la lista 'list'.
# @args
#    key: clave a buscar
#    list: lista
# @returns
#    Boolean

def varsInList(key, list):
	results = []
	for e in list:
		results.append(key in e)
	return (True in results)

# Funcion errorInList
# Retorna true si el error 'error' esta presente en algun elemento
# de la lista 'list', false en otro caso
# @args
#    error: error a buscar
#    list: lista
# @returns
#    Boolean

def errorInList(value, list):
	results = []
	for e in list:
		results.append(e['error'])
	return (value in results)

# Procedimiento numerador
# Numera las acciones en el xml
# @args
#    root: raiz del xml

def numerador(root):
	i = 0
	for child in root:
		child.set('orden', i)
		i += 1

# Procedimiento update_dict_zones
# Actualiza zonas de dicts existentes a sus instancias
# correspondientes
# @args
#    d_list: lista de dicts
#    i_list: lista de instancias

def update_dict_zones(d_list, i_list):
	for elem in d_list:
		for e in elem['zone']:
			for z in i_list:
				if (e['zone'] == z.name):
					e['zone'] = z

# Procedimiento event_generator
# Genera eventos a partir de listas y comparaciones
# @args
#	d_list: lista de dicts con eventos
#	e_list: lista de instancias de eventos

def event_generator(d_list, e_list):
	for d in d_list:
		prev_events = [x for x in e_list if x.position < d['orden']]
		# Si hay eventos previos a la accion
		try:
			min_distance = min([x.position for x in prev_events])
			closest_event = [x for x in prev_events if x.position == min_distance][0]
			executer = closest_event.executer
			if (d['unit'] == 's'):
				value = int(d['value'])
				time_unit = datetime.timedelta(seconds=value)
			elif (d['unit'] == 'm'):
				value = int(d['value'])
				time_unit = datetime.timedelta(minutes=value)
			else:
				value = int(d['value'])
				time_unit = datetime.timedelta(hours=value)
			e_list.append(TimeEvent(executer, d['orden'], d['unit'], \
				time_unit, d['expr']))
		# Si no hay nada antes del delay
		except:
			if (d['unit'] == 's'):
				value = int(d['value'])
				time_unit = datetime.timedelta(seconds=value)
			elif (d['unit'] == 'm'):
				value = int(d['value'])
				time_unit = datetime.timedelta(minutes=value)
			else:
				value = int(d['value'])
				time_unit = datetime.timedelta(hours=value)
			e_list.append(TimeEvent(None, d['orden'], d['unit'], \
				time_unit, d['expr']))

# Procedimiento setPropertyEventsGenerator
# Genera eventos property changing a partir de set-device-property
# @args
#    sim: resultado de lectura de xml 
#    sim_child: linea de la simulacion con set-device-property
#    zone: instancia de clase zone donde se ubica el device
#    device: dispositivo modificado por set-device-property
#    changes: dict property/value del device
#    elist: lista de eventos

def changePropertyEventGenerator(sim, sim_child, zone, device, changes, elist):
	last_move = [x for x in sim if x.attrib['orden'] < sim_child.attrib['orden'] \
				and x.tag == 'move-person-zone' and \
				x.attrib['zoneId'].lower().replace(' ','') == zone.name]
	if (last_move):
		executer = last_move[len(last_move) - 1].attrib['personId']
		executer = [p for p in pclass if p.name == executer]
		# Creo instancias
		elist.append(PropertyChangingEvent(executer, sim_child.attrib['orden'], \
			device, changes))
	else:
		# No puedo inferir por el ultimo movimiento a la zona del device
		# porque no hay
		elist.append(PropertyChangingEvent(None, sim_child.attrib['orden'], \
			device, changes))


# Funcion positionOrdering
# Funciona de key para el sort()
# @args
#    event: evento de la lista de eventos
# @returns
#    Int, posicion en la simulacion de un evento

def positionOrdering(event):
	return event.position

# Procedimiento deviceTimeOn
# Aniade a lista de errores aquellos eventos que excedieron tiempo max de device on
# @args
#    events: lista de eventos a revisar en busca de turn off
#    e: evento puntual de turn on
#    error_list: lista de errores al cual aniadir nuevos
#    time_sim: hora de inicio de la simulacion

def deviceTimeOn(events, e, error_list, time_sim):
	# Depende del tipo de device, tendremos diferentes chequeos a realizar
	if (e.device.type_name == 'iCasa.DimmerLight'):
		# Si es una dimmer light
		device_off = [x for x in events if isinstance(x, PropertyChangingEvent) and \
				x.position > e.position and \
				x.changedProperty['property'] == 'dimmerLight.powerLevel' and \
				float(e.changedProperty['value']) == 0 and \
				e.device.name == x.device.name]
	elif (e.device.type_name == 'iCasa.Heater'):
		# Si  es un heater
		device_off = [x for x in events if isinstance(x, PropertyChangingEvent) and \
				x.position > e.position and \
				x.changedProperty['property'] == 'heater.powerLevel' and \
				float(e.changedProperty['value']) == 0 and \
				e.device.name == x.device.name]
	elif (e.device.type_name == 'iCasa.Cooler'):
		# Si es un cooler
		device_off = [x for x in events if isinstance(x, PropertyChangingEvent) and \
				x.position > e.position and \
				x.changedProperty['property'] == 'cooler.powerLevel' and \
				float(e.changedProperty['value']) == 0 and \
				e.device.name == x.device.name]
	else:
		# Si es binary light
		device_off = [x for x in events if isinstance(x, PropertyChangingEvent) and \
				x.position > e.position and \
				x.changedProperty['property'] == 'binaryLight.powerStatus' and \
				e.changedProperty['value'] == 'false' and \
				e.device.name == x.device.name]

	# Si fue apagado
	if (device_off):
		if (e.device.type_name == 'iCasa.DimmerLight' or e.device.type_name == 'iCasa.BinaryLight'):
			# Primero chequeo horario de encendido
			day_time_light_on = [x.value for x in events if isinstance(x, TimeEvent) and \
								x.position < e.position]
			if (day_time_light_on):
				current_time = time_sim + reduce((lambda x, y: x + y), day_time_light_on)
				current_time = (datetime.datetime.min + current_time).time()
				if (NIGHTTIME_MAX > current_time and current_time > datetime.time(0, 0, 0)):
					# Problema, luz encendida a horas inadecuadas
					error_list.append({'position': e.position, 'executer': e.executer, \
						'error': 'Lights on at wrong time'})
		device_off_position == device_off[0].position
		delays = [x.value for x in events if isinstance(x, TimeEvent) and \
		x.position > e.position and x.position < device_off_position]
		# Tiempo que se mantuvo encendido
		#time_since_on = (datetime.datetime.min + reduce((lambda x, y: x + y), delays)).time()
		time_since_on = reduce((lambda x, y: x + y), delays)
		# Si excede tiempo maximo, hay problemas
		if (e.device.type_name == 'iCasa.DimmerLight'):
			# Si es dimmer light
			if (time_since_on > MAX_TIME_LIGHT_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'DimmerLight exceeded MAX time ON'})
		elif (e.device.type_name == 'iCasa.Heater'):
			# Si es heater
			if (time_since_on > MAX_TIME_HEAT_COOL_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'Heater exceeded MAX time ON'})
		elif (e.device.type_name == 'iCasa.Cooler'):
			# Si es cooler
			if (time_since_on > MAX_TIME_HEAT_COOL_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'Cooler exceeded MAX time ON'})
		else:
			# Si es binary light
			if (time_since_on > MAX_TIME_LIGHT_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'BinaryLight exceeded MAX time ON'})

	# Si no apagaron el device, revisamos el tiempo que estuvo encendido en la sim
	else:
		if (e.device.type_name == 'iCasa.DimmerLight' or e.device.type_name == 'iCasa.BinaryLight'):
			# Primero chequeo horario de encendido
			day_time_light_on = [x.value for x in events if isinstance(x, TimeEvent) and \
								x.position < e.position]
			if (day_time_light_on):
				current_time = time_sim + reduce((lambda x, y: x + y), day_time_light_on)
				current_time = (datetime.datetime.min + current_time).time()
				if (NIGHTTIME_MAX > current_time and current_time > datetime.time(0, 0, 0)):
					# Problema, luz encendida a horas inadecuadas
					error_list.append({'position': e.position, 'executer': e.executer, \
						'error': 'Lights on at wrong time'})
		delays = [x.value for x in events if isinstance(x, TimeEvent) and \
		x.position > e.position]
		if (delays):
			# Tiempo que se mantuvo encendido
			#time_since_on = (datetime.datetime.min + reduce((lambda x, y: x + y), delays)).time()
			time_since_on = reduce((lambda x, y: x + y), delays)
		else:
			#time_since_on = (datetime.datetime.min).time()
			time_since_on = datetime.timedelta(seconds=0)
		# Si excede tiempo maximo, hay problemas
		if (e.device.type_name == 'iCasa.DimmerLight'):
			# Si es dimmer light
			if (time_since_on > MAX_TIME_LIGHT_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'DimmerLight exceeded MAX time ON'})
		elif (e.device.type_name == 'iCasa.Heater'):
			# Si es heater
			if (time_since_on > MAX_TIME_HEAT_COOL_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'Heater exceeded MAX time ON'})
		elif (e.device.type_name == 'iCasa.Cooler'):
			# Si es cooler
			if (time_since_on > MAX_TIME_HEAT_COOL_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'Cooler exceeded MAX time ON'})
		else:
			# Si es binary light
			if (time_since_on > MAX_TIME_LIGHT_ON):
				error_list.append({'position': e.position, 'executer': e.executer, \
					'error': 'BinaryLight exceeded MAX time ON'})

# Procedimiento possibleSedentarism
# Analiza patrones de tiempo para hallar problemas con no salir de la habitacion
# pues no hay moves futuros
# @args
#    events: lista de eventos a recorrer para comparaciones
#    e: evento move inicial
#    current_time: tiempo actual de la simulacion
#    error_list: lista de errores al cual aniadir nuevos

def possibleSedentarism(events, e, current_time, error_list):
	start_stuck_time = (datetime.datetime.min + current_time).time()
	# Hallamos tiempo en reposo
	delays_post_move = [x.value for x in events if isinstance(x, TimeEvent) and \
			x.position > e.position]
	if (delays_post_move):
		time_post_move = reduce((lambda x, y: x + y), delays_post_move)
		# Tiempo en habitacion sin moverme a otro lado contando tiempo actual
		lazy_time = current_time + time_post_move
		lazy_time = (datetime.datetime.min + lazy_time).time()
		# Si es de dia y estuve muchas horas encerrado sin salir
		if (DAYTIME_MIN < lazy_time and DAYTIME_MAX > lazy_time and \
			NIGHTTIME_MIN > start_stuck_time and time_post_move > MAX_STILL_TIME_BEDROOM):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Not getting out of room for much time'})

# Procedimiento possibleSedentarismBM
# Analiza patrones de tiempo para hallar problemas con no salir de la habitacion
# cuando hay moves tiempo despues
# @args
#    events: lista de eventos a recorrer para comparaciones
#    e: evento move inicial
#    current_time: tiempo actual de la simulacion
#    next_moves: lista de proximos movimientos del mismo executer
#    error_list: lista de errores al cual aniadir nuevos

def possibleSedentarismBM(events, e, current_time, next_moves, error_list):
	# En formato time
	start_stuck_time = (datetime.datetime.min + current_time).time()								
	# Se debe hallar la distancia en tiempo entre cada move
	delays_bw_moves = [x.value for x in events if isinstance(x, TimeEvent) and \
				x.position > e.position and x.position < next_moves[0].position]
	if (delays_bw_moves):
		time_between_moves = reduce((lambda x, y: x + y), delays_bw_moves)
		# Tiempo entre moves considerando tiempo actual de la sim
		finish_stuck_time = current_time + time_between_moves
		finish_stuck_time = (datetime.datetime.min + current_time).time()
		if (DAYTIME_MIN < finish_stuck_time and DAYTIME_MAX > finish_stuck_time and \
			NIGHTTIME_MIN > start_stuck_time and time_between_moves > MAX_STILL_TIME_BEDROOM):
			elist.append({'position': e.position, 'executer': e.executer, \
				'error': 'Not getting out of room for much time'})

# Procedimiento possibleAccident
# Analiza patrones de tiempo para hallar problemas con no salir de alguna habitacion
# puntual a excepcion de bedroom
# @args
#    events: lista de eventos a recorrer para comparaciones
#    e: evento move inicial
#    e_zone: nombre zona pre-procesado
#    error_list: lista de errores al cual aniadir nuevos

def possibleAccident(events, e, e_zone, error_list):
	# Determinamos tiempo post movimiento
	delays_post_move = [x.value for x in events if isinstance(x, TimeEvent) and \
				x.position > e.position]
	if (delays_post_move):
		time_post_move = reduce((lambda x, y: x + y), delays_post_move)
		# Identificamos problemas
		if (e_zone == 'bathroom' and time_post_move > MAX_STILL_TIME_BATHROOM):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in BATHROOM'})
		elif (e_zone == 'livingroom' and time_post_move > MAX_STILL_TIME_LIVINGROOM):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in LIVING ROOM'})
		elif (e_zone == 'kitchen' and time_post_move > MAX_STILL_TIME_KITCHEN):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in KITCHEN'})
		elif (e_zone == 'hallway' and time_post_move > MAX_STILL_TIME_HALLWAY):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in HALLWAY'})

# Procedimiento possibleAccidentBM
# Analiza patrones de tiempo para hallar problemas con no salir de alguna habitacion
# puntual a excepcion de bedroom
# @args
#    events: lista de eventos a recorrer para comparaciones
#    e: evento move inicial
#    e_zone: nombre de zona pre-procesado
#    next_moves: lista de proximos movimientos del mismo executer
#    error_list: lista de errores al cual aniadir nuevos

def possibleAccidentBM(events, e, e_zone, next_moves, error_list):
	# Determinamos tiempo entre movimientos
	delays_bw_moves = [x.value for x in events if isinstance(x, TimeEvent) and \
				x.position > e.position and x.position < next_moves[0].position]
	if (delays_bw_moves):
		time_between_moves = reduce((lambda x, y: x + y), delays_bw_moves)
		# Identificamos problemas
		if (e_zone == 'bathroom' and time_between_moves > MAX_STILL_TIME_BATHROOM):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in BATHROOM'})
		elif (e_zone == 'livingroom' and time_between_moves > MAX_STILL_TIME_LIVINGROOM):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in LIVING ROOM'})
		elif (e_zone == 'kitchen' and time_between_moves > MAX_STILL_TIME_KITCHEN):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in KITCHEN'})
		elif (e_zone == 'hallway' and time_between_moves > MAX_STILL_TIME_HALLWAY):
			error_list.append({'position': e.position, 'executer': e.executer, \
				'error': 'Possible accident in HALLWAY'})

#################################
# Clases                        #
#################################

# Clase Zone
# Modela las zonas del simulador
#
# @attrs
#    position: posicion de aparicion en script
#    name: nombre de la zona
#    variables: dict de variables asociadas a zona

class Zone:

	# Inicializador
	def __init__(self, position, name, variables):
		self.position = position
		self.name = name
		self.variables = variables

	# Representacion en string
	def __str__(self):
		return self.name

# Clase Device
# Modela los dispositivos del simulador
#
# @attrs
#    position: posicion de aparicion en script
#    name: nombre de dispositivo
#    type: tipo de dispositivo
#    related_events: dict de eventos de ese dispositivo
#    zones: lista de zonas donde se ubico el dispositivo

class Device:

	# Inicializador
	def __init__(self, position, name, type_name, related_events, zones):
		self.position = position
		self.name = name
		self.type_name = type_name
		self.related_events = related_events
		self.zones = zones

	def __str__(self):
		return 'Dispositivo {self.name} de tipo {self.type_name}'.format(self=self)

# Class Person
# Modela a las personas del simulador
#
# @attrs
#    name: nombre de la persona
#    type: tipo de persona
#    zones: lista de zonas donde se ubico la persona
#    aggir_const: dict de variables AGGIR

class Person:

	# Inicializador
	def __init__(self, name, type_name, zones, aggir_const):
		self.name = name
		self.type_name = type_name
		self.zones = zones
		self.aggir_const = aggir_const

	def __str__(self):
		return '{self.name}'.format(self=self)

# Clase Event
# Modela una situacion puntual en el simulador
#
# @attrs
#    executer: sujeto involucrado con la accion
#    position: posicion del evento
#    event: evento ocurrido

class Event:

	# Inicializador
	def __init__(self, executer, position, event):
		self.executer = executer
		self.position = position
		self.event = event

	def __str__(self):
		return '{self.event} en posicion {self.position} relacionado con '.format(self=self) \
		+ 'persona {self.executer}'.format(self=self)

# Clase MoveEvent - Subclase de Event
# Modela movimientos de zonas para personas
#
# @attrs
#    zone: zone a la cual se envia a la persona

class MoveEvent(Event):

	# Inicializador
	def __init__(self, executer, position, event, zone):
		self.executer = executer
		self.position = position
		self.event = event
		self.zone = zone

	def __str__(self):
		return '{self.event} en posicion {self.position} relacionado con '.format(self=self) \
		+ 'persona {self.executer} a zona {self.zone}'.format(self=self)

# Clase VarChangingEvent - Subclase de Event
# Modela cambios de variables en zonas
#
# @attrs
#    change: dict de variable/value modificado

class VarChangingEvent(Event):

	# Inicializador
	def __init__(self, executer, position, event, change):
		self.executer = executer
		self.position = position
		self.event = event
		self.change = change

# Clase TimeEvent - Subclase de Event
# Modela los delays del simulador
#
# @attrs
#    unit: unidad de tiempo
#    value: cantidad de unidades de tiempo

class TimeEvent(Event):

	# Inicializador
	def __init__(self, executer, position, unit, value, event):
		self.executer = executer
		self.position = position
		self.unit = unit
		self.value = value
		self.event = event

	def __str__(self):
		return '{self.event} relacionado con persona {self.executer}'.format(self=self)

# Clase PropertyChangingEvent
# Modela eventos que cambian propiedades de devices
#
# @attrs
#    executer: sujeto involucrado en la accion
#    position: posicion del evento
#    device: dispositivo modificado
#    changedProperty: dict de prop(s) modificada(s) con value

class PropertyChangingEvent:

	# Inicializador
	def __init__(self, executer, position, device, changedProperty):
		self.executer = executer
		self.position = position
		self.device = device
		self.changedProperty = changedProperty

	def __str__(self):
		return 'Cambio en {self.device.name} de tipo {self.device.type_name}'.format(self=self) \
		+ ' causado por {self.executer}'.format(self=self)

# Clase Situation
# Modela una situacion en el simulador, posee un
# inicio, acciones dentro de ella, y un final
#
# @attrs
#    first_act: accion inicial de una situacion
#    events: lista de eventos ocurridos luego del inicio
#    last_act: ultimo evento de una situacion

class Situation:

	# Inicializador
	def __init__(self, first_act, events, last_act):
		self.first_act = first_act
		self.events = events
		self.last_act = last_act

	# Retorna accion inicial
	def get_first_event(self):
		return self.first_act

	# Retorna lista de acciones
	def get_mid_events(self):
		return self.events

	# Retorna accion final
	def get_last_event(self):
		return self.last_act

#################################
# Codigo                        #
#################################

# Funcion principal
def main(argv):
	# Si pasaron menos de tres argumentos
	if (len(argv) < 3):
		print('Usage: analyzer.py input_file.bhv main_door_room')
		sys.exit(1)
	# Si pasaron mas de tres argumentos
	elif (len(argv) > 3):
		print('Usage: analyzer.py input_file.bhv main_door_room')
		sys.exit(2)
	# Pasaron los tres argumentos necesarios
	else:
		# Genero ElementTree a partir del archivo
		simulacion = ET.parse(argv[1])
		behavior = simulacion.getroot()
		main_door_room = argv[2]

		try:
			# Si hay fecha/hora
			starttime = behavior.attrib['startdate']
			# Obtengo fecha
			date_sim = starttime.split('-')[0]
			# Obtengo hora
			time_sim = starttime.split('-')[1]
			hrs = int(time_sim.split(':')[0])
			mins = int(time_sim.split(':')[1])
			secs = int(time_sim.split(':')[2])
			time_sim = datetime.timedelta(hours=hrs, minutes=mins, seconds=secs)
		except:
			print('No starting time given. Setting default: 00:00:00')
			time_sim = datetime.timedelta(hours=0, minutes=0, seconds=0)

		# Numerando acciones
		numerador(behavior)

		# Listas para almacenar objetos de cada tipo descrito
		zones = []
		devices = []
		people = []
		delay = []

		# Lista de dics para zones, devices, people, eventos de tiempo,
		# situaciones y errores
		zlist = []
		dlist = []
		plist = []
		tlist = []
		slist = []
		elist = []

		# Listas de instancias de clases para personas, devices, zonas, eventos
		# y situaciones
		pclass = []
		dclass = []
		zclass = []
		eclass = []
		sclass = []

		# Lista de tiempo total para una simulacion
		total_time = []

		# Veces que se fue al banio en toda la sim
		bathroom_times = []

		# Veces que sali
		times_out = []

		# Veces que abri el closet
		times_wd_opened = []

		# Lleno listas de todas las zones, devices, people y delays
		for child in behavior:
			if (child.tag == 'create-zone'):
				zones.append(child)
			elif (child.tag == 'create-device'):
				devices.append(child)
			elif (child.tag == 'create-person'):
				people.append(child)
			elif (child.tag == 'delay'):
				delay.append(child)

		# Obtengo variables asociadas a cada zona
		if (zones):
			for zone in zones:
				zdic = {}
				zdic['zone'] = zone.attrib['id'].lower().replace(' ','')
				zdic['orden'] = zone.attrib['orden']
				for child in behavior:
					if (child.tag == 'add-zone-variable' and \
						child.attrib['zoneId'].lower().replace(' ','') == zdic['zone']):
						# Si el dic ya fue creado, actualizo
						if ('vars' in zdic):
							tmp = zdic['vars']
							tmp.update({child.attrib['variable']: None})
							zdic['vars'] = tmp
						# Creo el dic en otro caso
						else:
							zdic['vars'] = {child.attrib['variable']: None}
				# Lleno lista de dics
				zlist.append(zdic)

			# Coloco valores a las variables, reviso si las hay
			if (varsInList('vars', zlist)):
				for z in zlist:
					for child in behavior:
						if (child.tag == 'modify-zone-variable' and \
							child.attrib['zoneId'].lower().replace(' ','') == z['zone']):
							tmp = z['vars']
							tmp[child.attrib['variable']] = child.attrib['value']
							z['vars'] = tmp

		# TENGO TODO DE LAS ZONAS

		if (devices):
			# Obtengo devices y sus zonas
			for device in devices:
				ddic = {}
				ddic['device'] = device.attrib['id']
				ddic['type'] = device.attrib['type']
				ddic['orden'] = device.attrib['orden']
				for child in behavior:
					if (child.tag == 'move-device-zone' and child.attrib['deviceId'] == device.attrib['id']):
						# Si existe el key zone, aniado el dic a la lista
						if ('zone' in ddic):
							tmp = ddic['zone']
							tmp.append({'orden': child.attrib['orden'], \
								'zone': child.attrib['zoneId'].lower().replace(' ','')})
							ddic['zone'] = tmp
						# Creo la nueva lista
						else:
							ddic['zone'] = [{'orden': child.attrib['orden'], \
							'zone': child.attrib['zoneId'].lower().replace(' ','')}]
				dlist.append(ddic)

		# Tengo devices con id, type y zona donde esta

		# PENDIENTE: Con remove habria que sacar el device de la lista

			for d in dlist:
				for child in behavior:
					if ('deviceId' in child.attrib and child.attrib['deviceId'] == d['device']):
						if (child.tag != 'move-device-zone'):
							# Si existe el key events, aniado el dic a la lista
							if ('events' in d):
								tmp = d['events']
								# Si se aniade una propiedad, hago dic especial
								if (child.tag == 'set-device-property'):
									tmp.append({'orden': child.attrib['orden'], 'event': child.tag,
												'property': child.attrib['property'], 'value': child.attrib['value']})
								# Creo dic normal en otro caso
								else:
									tmp.append({'orden': child.attrib['orden'], 'event': child.tag})
								d['events'] = tmp
							# Creo lista de eventos
							else:
								# Si se aniade una propiedad, hago dic especial
								if (child.tag == 'set-device-property'):
									d['events'] = [{'orden': child.attrib['orden'], 'event': child.tag,
													'property': child.attrib['property'], 'value': child.attrib['value']}]
								# Creo dic normal en otro caso
								else:
									d['events'] = [{'orden': child.attrib['orden'], 'event': child.tag}]

		# TENGO DEVICES CON TODOS LOS EVENTOS OCURRIDOS CON ELLOS, ADEMAS DE ZONAS, ORDEN, TIPOS E ID

		if (people):
			# Obtengo personas
			for person in people:
				pdic = {}
				pdic['name'] = person.attrib['id']
				pdic['type'] = person.attrib['type']
				# Obtengo las zonas de cada uno
				for child in behavior:
					if (child.tag == 'move-person-zone' and child.attrib['personId'] == person.attrib['id']):
						# Si existe el key zone, aniadimos la zona nueva al dic
						if ('zone' in pdic):
							tmp = pdic['zone']
							tmp.append({'orden': child.attrib['orden'], \
								'zone': child.attrib['zoneId'].lower().replace(' ','')})
							pdic['zone'] = tmp
						# Creo dic de zonas en otro caso
						else:
							pdic['zone'] = [{'orden': child.attrib['orden'], \
							'zone': child.attrib['zoneId'].lower().replace(' ','')}]
				plist.append(pdic)

		# TENGO A LAS PERSONAS Y SUS ZONAS CORRESPONDIENTES

		# Obtengo estructuras de tiempo
		if (delay):
			for d in delay:
				tdict = {}
				tdict['expr'] = d.tag
				tdict['orden'] = d.attrib['orden']
				tdict['value'] = d.attrib['value']
				tdict['unit'] = d.attrib['unit']
				tlist.append(tdict)

		# TENGO TODOS LOS DELAY DESGLOSADOS, ES UN EVENT

		if (zlist):
			# Generando instancias de clases para zonas
			for elem in zlist:
				zclass.append(Zone(elem['orden'], elem['zone'], elem['vars']))

			# Actualizando zonas en dict de devices
			update_dict_zones(dlist, zclass)

			# Actualizando zonas en dict de people
			update_dict_zones(plist, zclass)

		if (dlist):
			# Generando instancias de clases para dispositivos
			for elem in dlist:
				try:
					dclass.append(Device(elem['orden'], elem['device'], elem['type'], elem['events'], elem['zone']))
				except:
					dclass.append(Device(elem['orden'], elem['device'], elem['type'], [], elem['zone']))

		if (plist):
			# Generando instancias de clases para personas
			for elem in plist:
				pclass.append(Person(elem['name'], elem['type'], elem['zone'], AGGIR_CONST))

		# Generando instancias de eventos

		# CASO 1: move-device-zone

		# No hay personas generadas
		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'move-device-zone'):
					tmp = [c for c in behavior if c.attrib['orden'] < child.attrib['orden']]
					if (tmp):
						# Caso setup
						if (tmp[len(tmp) - 1].tag == 'create-device'):
							pass
						# Caso movimiento de persona previo
						elif (tmp[len(tmp) - 1].tag == 'move-person-zone'):
							executer = [p for p in pclass if p.name == tmp[len(tmp) - 1].attrib['personId']][0]
							eclass.append(Event(executer, child.attrib['orden'], child.tag))

		# CASO 2: modify-zone-variable

		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'modify-zone-variable'):
					tmp = [c for c in behavior if c.attrib['orden'] < child.attrib['orden']]
					if (tmp):
						# Caso setup
						if (tmp[len(tmp) - 1].tag == 'add-zone-variable'):
							pass
						# Casos de cambio por movimiento de persona
						elif (tmp[len(tmp) - 1].tag == 'move-person-zone'):
							executer = [p for p in pclass if p.name == tmp[len(tmp) - 1].attrib['personId']][0]
							zone = [z for z in zclass if \
									z.name == child.attrib['zoneId'].lower().replace(' ','')][0]
							dictionary = {'variable': child.attrib['variable'], 'value': child.attrib['value'], \
											'zone': zone}
							eclass.append(VarChangingEvent(executer, child.attrib['orden'], child.tag, \
								dictionary))
						elif (tmp[len(tmp) - 1].tag == 'move-device-zone' \
							and tmp[len(tmp) - 2].tag == 'move-person-zone'):
							executer = [p for p in pclass if p.name == tmp[len(tmp) - 2].attrib['personId']][0]
							zone = [z for z in zclass if \
									z.name == child.attrib['zoneId'].lower().replace(' ','')][0]
							dictionary = {'variable': child.attrib['variable'], 'value': child.attrib['value'], \
											'zone': zone}
							eclass.append(VarChangingEvent(executer, child.attrib['orden'], child.tag, \
								dictionary))
						# Casos de modificaciones por executer mas cercano en script
						else:
							last_move = [x for x in behavior if x.attrib['orden'] < child.attrib['orden'] and \
											x.tag == 'move-person-zone' and \
											x.attrib['zoneId'] == child.attrib['zoneId'].lower().replace(' ','')]
							if (last_move):
								zone = [z for z in zclass if \
										z.name == child.attrib['zoneId'].lower().replace(' ','')][0]
								dictionary = {'variable': child.attrib['variable'], 'value': child.attrib['value'], \
												'zone': zone}
								# Ultima persona que se movio a la zona
								executer = last_move[len(last_move) - 1].attrib['personId']
								executer = [p for p in pclass if p.name == executer][0]
								eclass.append(VarChangingEvent(executer, child.attrib['orden'], child.tag, \
									dictionary))

		# CASO 3: set-device-property

		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'set-device-property'):
					tmp = [x for x in behavior if x.attrib['orden'] < child.attrib['orden']]
					if (tmp):
						# caso setup inicial 1
						if (tmp[len(tmp) - 1].tag == 'create-device'):
							pass
						elif (tmp[len(tmp) - 2].tag == 'create-device' and \
							tmp[len(tmp) - 1].tag == 'move-device-zone'):
							pass
						# variaciones en simulacion
						else:
							device = [x for x in dclass if x.name == child.attrib['deviceId']][0]
							changedAttr = child.attrib['property']
							changedValue = child.attrib['value']
							changes = {'property': changedAttr, 'value': changedValue}
							# Si hay solo un user
							if (len(people) == 1):
								executer = pclass[0]
								# Creo instancias
								eclass.append(PropertyChangingEvent(executer, child.attrib['orden'], \
									device, changes))
							else:
								# Buscamos zona del device, los mismo no suelen ser movibles
								num_zones_dev = len(device.zones)
								if (num_zones_dev == 1):
									zone = device.zones[0]['zone']
									# Llamo a la funcion adecuada
									changePropertyEventGenerator(behavior, child, zone, device, changes, eclass)
								else:
									# Busco la zona en device cuyo orden sea el mas cercano al orden
									# del set-device-property actual
									nearest_zone = [x['zone'] for x in device.zones if \
																x['orden'] < child.attrib['orden']][-1]
									# Llamo a la funcion adecuada
									changePropertyEventGenerator(behavior, child, nearest_zone, device, changes, eclass)

		# CASO 4: fault device

		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'fault-device'):
					dev = child.attrib['deviceId']
					try:
						# Ultima ubicacion del device
						place = [x.attrib['zoneId'].lower().replace(' ','') for x in behavior if \
						x.attrib['orden'] < child.attrib['orden'] and x.tag == 'move-device-zone' \
						and x.attrib['deviceId'] == dev][0]
						place = [x for x in zclass if x.name == place][0]
						tmp = [x for x in behavior if x.attrib['orden'] < child.attrib['orden'] \
						and x.tag == 'move-person-zone' and \
						x.attrib['zoneId'].lower().replace(' ','') == place.name]
						# Si hay eventos previos a la accion
						if (tmp):
							# Persona que interactuo mas recientemente con ubicacion device
							min_distance = min([x.attrib['orden'] for x in tmp])
							closest_event = [x for x in tmp if x.attrib['orden'] == min_distance][0]
							executer = [x for x in pclass if x.name == closest_event.attrib['personId']][0]
							eclass.append(Event(executer, child.attrib['orden'], child.tag))
						else:
							# Fault natural
							eclass.append(Event(None, child.attrib['orden'], child.tag))
					# No hay movimiento a zona del device previo al fault del mismo
					except:
						pass

		# CASO 5: move-person-zone

		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'move-person-zone'):
					executer = [x for x in pclass if x.name == child.attrib['personId']][0]
					zone = [x for x in zclass if x.name == child.attrib['zoneId'].lower().replace(' ','')][0]
					eclass.append(MoveEvent(executer, child.attrib['orden'], child.tag, zone))

		# CASO x: delay - DEBE IR AL FINAL

		# Si hay acciones en lista de events, aniado a la lista
		if (eclass):
			event_generator(tlist, eclass)
		# Si no hay eventos creados aun
		else:
			# Creo primer evento delay
			if (tlist[0]['unit'] == 's'):
				value = int(tlist[0]['value'])
				time_unit = datetime.timedelta(seconds=value)
			elif (tlist[0]['unit'] == 'm'):
				value = int(tlist[0]['value'])
				time_unit = datetime.timedelta(minutes=value)
			else:
				value = int(tlist[0]['value'])
				time_unit = datetime.timedelta(hours=value)
			eclass.append(TimeEvent(None, tlist[0]['orden'], tlist[0]['unit'], \
				time_unit, tlist[0]['expr']))
			# Llamo al event_generator sin contar el primer elemento de la lista
			if (len(tlist) > 1):
				event_generator(tlist[1:], eclass)

		# Ordenando segun posicion 
		eclass.sort(key=positionOrdering)

		# GENERANDO SITUACIONES

		# Contador
		counter = 0
		# Aux sera lista de indices de eclass donde hay fin de actividad
		aux = []
		for elem in eclass:
			if (isinstance(elem, TimeEvent)):
				if (elem.value == datetime.timedelta(0) and elem.unit == 's'):
					aux.append(counter)
			counter = counter + 1

		# Formo subconjuntos de eventos que seran situaciones
		start = 0
		for elem in aux:
			slist.append(eclass[start:elem])
			start = elem + 1

		# Genero lista de instancias de situaciones
		for elem in slist:
			size = len(elem)
			sclass.append(Situation(elem[0], elem[1:size - 1], elem[size - 1]))

		# TENGO TODAS LAS SITUACIONES DEL SCRIPT DE SIMULACION

		# Analizamos situaciones para hallar posibles problemas
		for s in sclass:
			eventos = [s.get_first_event()] + s.get_mid_events() + [s.get_last_event()]
			for e in eventos:
				if (isinstance(e, PropertyChangingEvent)):
					# 1. Si hay inundacion
					if (e.device.type_name == 'iCasa.FloodSensor' and \
						e.changedProperty['value'] == 'true'):
						elist.append({'position': e.position, 'executer': e.executer, \
							'error': 'FloodSensor detected a problem'})
					# 2. Luces siempre encendidas
					# 2.1 Binary Lights
					elif (e.device.type_name == 'iCasa.BinaryLight' and \
						e.changedProperty['property'] == 'binaryLight.powerStatus' and \
						e.changedProperty['value'] == 'true'):
						# Determino si hay problemas con la funcion adecuada
						deviceTimeOn(eventos, e, elist, time_sim)
					# 2.2 Dimmer Lights
					elif (e.device.type_name == 'iCasa.DimmerLight' and \
						e.changedProperty['property'] == 'dimmerLight.powerLevel' and \
						float(e.changedProperty['value']) >= 0):
						# Determino si hay problemas con la funcion adecuada
						deviceTimeOn(eventos, e, elist, time_sim)
					# 3. Altas/bajas temperaturas
					# 3.1 Heater
					elif (e.device.type_name == 'iCasa.Heater' and \
						e.changedProperty['property'] == 'heater.powerLevel' and \
						float(e.changedProperty['value']) >= 0):
						# Determino si hay problemas con la funcion adecuada
						deviceTimeOn(eventos, e, elist)
						# Reviso si el device esta activo con temperatura adecuada
						temp_zone = float(e.device.zones[0]['zone'].variables['Temperature'])
						if (temp_zone < MAX_TEMPERATURE):
							elist.append({'position': e.position, 'executer': e.executer, \
								'error': 'Heater on when no needed'})
					elif (e.device.type_name == 'iCasa.Cooler' and \
						e.changedProperty['property'] == 'cooler.powerLevel' and \
						float(e.changedProperty['value']) >= 0):
						# Determino si hay problema con la funcion adecuada
						deviceTimeOn(eventos, e, elist)
						# Reviso si el device esta activo con temperatura adecuada
						temp_zone = float(e.device.zones[0]['zone'].variables['Temperature'])
						if (temp_zone > MIN_TEMPERATURE):
							elist.append({'position': e.position, 'executer': e.executer, \
								'error': 'Cooler on when no needed'})
					# 4. Altos niveles de CO/CO2
					# 4.1 CO2
					elif (e.device.type_name == 'iCasa.COGasSensor' and \
						e.changedProperty['property'] == 'carbonMonoxydeSensor.currentConcentration' and \
						float(e.changedProperty['value']) >= MAX_CO_CONCENTRATION):
						elist.append({'position': e.position, 'executer': e.executer, \
							'error': 'HIGH CO CONCENTRATION'})
					# 4.2 CO
					elif (e.device.type_name == 'iCasa.CO2GasSensor' and \
						e.changedProperty['property'] == 'carbonDioxydeSensor.currentConcentration' and \
						float(e.changedProperty['value']) >= MAX_CO2_CONCENTRATION):
						elist.append({'position': e.position, 'executer': e.executer, \
							'error': 'HIGH CO2 CONCENTRATION'})
					# 5. Puerta principal abierta mucho tiempo
					elif (e.device.type_name == 'iCasa.DoorWindowSensor' and \
						e.changedProperty['value'] == 'true' and e.device.zones[0]['zone'].name == main_door_room):
						# Contamos la salida
						times_out.append(1)
						# Revisamos si se cerro
						closed_door = [x for x in eventos if isinstance(x, PropertyChangingEvent) and\
										x.device.type_name == 'iCasa.DoorWindowSensor' and \
										x.changedProperty['value'] == 'false' and \
										e.device.name == x.device.name and e.position < x.position]
						# Si la cerraron
						if (closed_door):
							# Revisamos tiempo entre open/close
							time_bw_closing = [x.value for x in eventos if isinstance(x, TimeEvent) and \
												x.position > e.position and x.position < closed_door[0].position]
							if (time_bw_closing):
								time_bw_closing = reduce((lambda x, y: x + y), time_bw_closing)
								if (time_bw_closing > MAX_MAIN_DOOR_OPEN_TIME):
									elist.append({'position': e.position, 'executer': e.executer, \
										'error': 'Main door LET OPENED for much time'})
						# Si no fue cerrada
						else:
							# Obtenemos tiempo transcurrido luego de apertura
							time_opened = [x.value for x in eventos if isinstance(x, TimeEvent) and \
											x.position > e.position]
							if (time_opened):
								time_opened = reduce((lambda x, y: x + y), time_opened)
								if (time_opened > MAX_MAIN_DOOR_OPEN_TIME):
									elist.append({'position': e.position, 'executer': e.executer, \
										'error': 'Main door LET OPENED for much time'})
					# 6. Sirena encendida
					elif (e.device.type_name == 'iCasa.Siren' and \
						e.changedProperty['value'] == 'true'):
						elist.append({'position': e.position, 'executer': e.executer, \
							'error': 'SIREN RINGING'})
					# 7. Andando, por mucho tiempo, de madrugada
					elif (e.device.type_name  == 'iCasa.PresenceSensor' and \
						e.changedProperty['value'] == 'true'):
						# Miramos si estuvo activo de madrugada
						current_time = [x.value for x in eventos if isinstance(x, TimeEvent) and \
										x.position < e.position]
						if (current_time):
							current_time = time_sim + reduce((lambda x, y: x + y), current_time)
							# Hora exacta de encendido
							current_time = (datetime.datetime.min + current_time).time()
							# Revisamos la duracion del encendido
							turn_off = [x for x in eventos if isinstance(x, PropertyChangingEvent) and \
										x.position > e.position and \
										x.device.name == e.device.name and \
										x.changedProperty['value'] == 'false']
							# Se apago
							if (turn_off):
								turn_off = turn_off[0]
								time_on = [x.value for x in eventos if isinstance(x, TimeEvent) and \
											x.position > e.position and x.position < turn_off.position]
								if (time_on):
									# Tiempo encendido hallado
									time_on = reduce((lambda x, y: x + y), time_on)
									if (time_on > datetime.timedelta(minutes=30) and \
										NIGHTTIME_MAX > current_time and \
										current_time > datetime.time(0, 0, 0)):
										# Hay un problema
										elist.append({'position': e.position, 'executer': e.executer, \
											'error': 'Wandering around at wrong time'})
							# No se apago
							else:
								# Hallamos el tiempo desde el encendido hasta el final de la sim
								time_on = [x.value for x in eventos if isinstance(x, TimeEvent) and \
											x.position > e.position]
								if (time_on):
									# Tiempo encendido hallado
									time_on = reduce((lambda x, y: x + y), time_on)
									if (time_on > datetime.timedelta(minutes=30) and \
										NIGHTTIME_MAX > current_time and \
										current_time > datetime.time(0, 0, 0)):
										# Hay un problema
										elist.append({'position': e.position, 'executer': e.executer, \
											'error': 'Wandering around at wrong time'})
				# Problemas relacionados a movimientos
				elif (isinstance(e, MoveEvent)):
					# 8. Sedentarismo
					e_zone = e.zone.name
					if (e.event == 'move-person-zone' and e_zone == 'bedroom'):
						# Obtenemos proximos moves a zones del mismo executer
						next_moves = [x for x in eventos if isinstance(x, MoveEvent) and \
									x.position > e.position and x.event == 'move-person-zone' and \
									x.executer == e.executer]
						# Sino hay mas
						if (len(next_moves) == 0):
							# Tiempo transcurrido al momento del move al bedroom
							delays = [x.value for x in eventos if isinstance(x, TimeEvent) and \
							x.position < e.position]
							if (delays):
								# Si hay algun delay
								time_before_move = reduce((lambda x, y: x + y), delays)
								current_time = time_sim + time_before_move
								# Detectamos problemas con funcion adecuada
								possibleSedentarism(eventos, e, current_time, elist)
							else:
								# Detectamos problemas con funcion adecuada y tiempo adecuado
								possibleSedentarism(eventos, e, time_sim, elist)
						# Si hay
						else:
							# Tiempo transcurrido al momento del move al bedroom
							delays = [x.value for x in eventos if isinstance(x, TimeEvent) and \
							x.position < e.position]
							if (delays):
								# Si hay algun delay
								time_before_move = reduce((lambda x, y: x + y), delays)
								current_time = time_sim + time_before_move
								# Uso funcion adecuada
								possibleSedentarismBM(eventos, e, current_time, next_moves, elist)
							else:
								# El move es el primer evento, uso funcion adecuada
								possibleSedentarismBM(eventos, e, time_sim, next_moves, elist)
					# 9. Accidentes
					# NO DETECTA DELAYS LUEGO DE MOVE-PERSON DE SETUP
					# Los 'accidentes' en bedroom quedan atrapados por el analisis de sedentarismo
					if (e.event == 'move-person-zone' and e_zone != 'bedroom'):
						# Obtenemos siguiente move a cualquier zona del mismo executer
						next_moves = [x for x in eventos if isinstance(x, MoveEvent) and \
									x.position > e.position and x.event == 'move-person-zone' and \
									x.executer == e.executer]
						# Si hay movimientos futuros
						if (next_moves):
							# Se debe ubicar tiempo inicial y tiempo entre movimientos
							delays = [x.value for x in eventos if isinstance(x, TimeEvent) and \
							x.position < e.position]
							if (delays):
								# Determinamos tiempo inicial
								time_before_move = reduce((lambda x, y: x + y), delays)
								current_time = time_sim + time_before_move
								# Llamo la funcion adecuada
								possibleAccidentBM(eventos, e, e_zone, next_moves, elist)
							else:
								# El move es el primer evento
								possibleAccidentBM(eventos, e, e_zone, next_moves, elist)
						# En otro caso
						else:
							# Se debe ubicar tiempo inicial y tiempo entre movimientos
							delays = [x.value for x in eventos if isinstance(x, TimeEvent) and \
							x.position < e.position]
							if (delays):
								# Determinamos tiempo inicial
								time_before_move = reduce((lambda x, y: x + y), delays)
								current_time = time_sim + time_before_move
								# Llamo la funcion adecuada
								possibleAccident(eventos, e, e_zone, elist)
							else:
								# El move es el primer evento
								possibleAccident(eventos, e, e_zone, elist)
				# Problemas relacionados con cambios de variables zonales
				elif (isinstance(e, VarChangingEvent)):
					e_zone = e.change['zone'].name
					# 7. Ubicacion al cocinar
					# Al detectar variacion de calor en la cocina, asumimos cooking
					if (e.change['variable'] == 'Temperature' and e_zone == 'kitchen'):
						prev_event = [x for x in behavior if x.attrib['orden'] == e.position - 1][0]
						# Ignoramos setup
						if (prev_event.tag == 'add-zone-variable'):
							pass
						elif (prev_event.tag != 'add-zone-variable'):
							# Caso en el que se apaga y luego se prende no merece analisis
							temp_eg_than_me = [x for x in eventos if isinstance(x, VarChangingEvent) and \
												x.position > e.position and \
												x.change['variable'] == 'Temperature' and \
												x.change['zone'].name == 'kitchen' and \
												x.change['value'] > e.change['value']]
							if (temp_eg_than_me):
								pass

							else:
								# Miramos si el calor disminuye en el futuro gracias al mismo que encendio
								temp_going_down = [x for x in eventos if isinstance(x, VarChangingEvent) and \
												x.position > e.position and \
												x.change['variable'] == 'Temperature' and \
												x.change['zone'].name == 'kitchen' and \
												x.change['value'] < e.change['value'] and \
												x.executer == e.executer]
								if (temp_going_down):
									temp_going_down = temp_going_down[0]
									# Debemos identificar si hay un move a otra zona en este espacio de tiempo
									next_zone_move = [x for x in eventos if isinstance(x, MoveEvent) and \
														x.position > e.position and \
														x.position < temp_going_down.position and \
														x.zone.name != 'kitchen' and x.executer == e.executer]
									if (next_zone_move):
										next_zone_move = next_zone_move[0]
										# Hallamos momento de retorno a la cocina
										returning_kitchen = [x for x in eventos if isinstance(x, MoveEvent) and \
															x.position > next_zone_move.position and \
															x.position < temp_going_down.position and \
															x.zone.name == 'kitchen' and x.executer == e.executer]
										if (returning_kitchen):
											returning_kitchen = returning_kitchen[0]
											# Calculamos tiempo entre ida y vuelta
											returning_kitchen_t = [x.value for x in eventos if isinstance(x, TimeEvent) and \
																		x.position > next_zone_move.position and \
																		x.position < returning_kitchen.position]
											if (returning_kitchen_t):
												returning_kitchen_t = reduce((lambda x, y: x + y), returning_kitchen_t)
												# Miramos si el tiempo fue superior al estipulado
												if (returning_kitchen_t > MAX_TIME_OUT_COOKING):
													# Hay problema
													elist.append({'position': e.position, 'executer': e.executer, \
														'error': 'Abandoning kitchen while cooking'})
								# Puede ser que alguien mas apago la llama o nadie mas
								else:
									# 1. Vemos si la apago alguien mas
									temp_going_down = [x for x in eventos if isinstance(x, VarChangingEvent) and \
														x.position > e.position and \
														x.change['variable'] == 'Temperature' and \
														x.change['zone'].name == 'kitchen' and \
														x.change['value'] < e.change['value']]
									if (temp_going_down):
										temp_going_down = temp_going_down[0]
										# El que prendio la llama se fue
										next_zone_move = [x for x in eventos if isinstance(x, MoveEvent) and \
															x.position > e.position and \
															x.position < temp_going_down.position and \
															x.zone.name != 'kitchen' and x.executer == e.executer]
										if (next_zone_move):
											next_zone_move = next_zone_move[0]
											# Calculamos tiempo que duro encendida la cocina hasta que alguien mas la apago
											someone_else_t = [x.value for x in eventos if isinstance(x, TimeEvent) and \
																	x.position > next_zone_move.position and \
																	x.position < temp_going_down.position]
											if (someone_else_t):
												someone_else_t = reduce((lambda x, y: x + y), someone_else_t)
												if (someone_else_t > MAX_TIME_OUT_COOKING):
													# Hay un problema con el que dejo eso encendido
													elist.append({'position': e.position, 'executer': e.executer, \
														'error': 'Abandoning kitchen while cooking'})
									# 2. No lo apago nadie
									else:
										# El que prendio la llama se fue
										next_zone_move = [x for x in eventos if isinstance(x, MoveEvent) and \
															x.position > e.position and \
															x.zone.name != 'kitchen' and x.executer == e.executer]
										if (next_zone_move):
											next_zone_move = next_zone_move[0]
											# Pude regresar y no apagarla
											returning_kitchen = [x for x in eventos if isinstance(x, MoveEvent) and \
																x.position > next_zone_move.position and \
																x.zone.name == 'kitchen' and \
																x.executer == e.executer]
											if (returning_kitchen):
												returning_kitchen = returning_kitchen[0]
												# Veo si me fui sin apagar
												leaving_again = [x for x in eventos if isinstance(x, MoveEvent) and \
																x.position > returning_kitchen.position and \
																x.zone.name != 'kitchen' and \
																x.executer == e.executer]
												if (leaving_again):
													leaving_again = leaving_again[0]
													# Calculo el tiempo hasta el final
													time_till_finish = [x.value for x in eventos if isinstance(x, TimeEvent) and \
																		x.position > leaving_again.position]
													if (time_till_finish):
														time_till_finish = reduce((lambda x, y: x + y), time_till_finish)
														if (time_till_finish > MAX_TIME_OUT_COOKING):
															# Hay problema con el que encendio la cocina
															elist.append({'position': e.position, 'executer': e.executer, \
																'error': 'Abandoning kitchen while cooking'})
											# Nunca regrese
											else:
												# Vemos si la temperatura es alta
												test_high_temp = [x for x in eventos if isinstance(x, VarChangingEvent) and \
																	x.position < e.position and x.executer == e.executer and \
																	x.change['variable'] == 'Temperature']
												if  (test_high_temp):
													test_high_temp = test_high_temp[len(test_high_temp) - 1]
													if (e.change['value'] < test_high_temp.change['value']):
														pass
													else:
														# Vemos el tiempo hasta el final de forma que sepamos si hay data suficiente
														# para evaluar
														time_till_finish = [x.value for x in eventos if isinstance(x, TimeEvent) and \
																			x.position > e.position]
														if (time_till_finish):
															time_till_finish = reduce((lambda x, y: x + y), time_till_finish)
															if (time_till_finish > MAX_TIME_OUT_COOKING):
																# Hay problema con el que encendio la cocina
																elist.append({'position': e.position, 'executer': e.executer, \
																	'error': 'Abandoning kitchen while cooking'})
										# No hay movimiento despues de mi, no puedo hacer inferencia sobre este issue
										else:
											pass
			# 10. Idas al banio, per situation
			# Hallamos la totalidad del tiempo por cada situacion
			situation_time = [x.value for x in eventos if isinstance(x, TimeEvent)]
			situation_time = reduce((lambda x, y: x + y), situation_time)
			total_time.append(situation_time)
			# Si el tiempo de una situacion es mayor a 4 horas, se debio ir, idealmente
			# al menos una vez a banio
			if (situation_time > IDEAL_TIME_BW_MICTURITION):
				# Revisamos si fuimos al menos una vez al banio en ese periodo
				went_to_bathroom = [x for x in eventos if isinstance(x, MoveEvent) and \
									x.event == 'move-person-zone' and x.zone.name == 'bathroom']
				# Suponiendo una unica persona, si hay eventos, los contamos
				times_bathroom = len(went_to_bathroom)
				if (times_bathroom > 0):
					pass
					#print('No apparent micturating problem')
				else:
					# Hay problema
					executer = [x for x in pclass][0]
					elist.append({'position': None, 'executer': executer.name, \
						'error': 'Irregular micturating time'})

		# 10. Idas al banio, whole simulation
		total_time = reduce((lambda x, y: x + y), total_time)
		if (total_time > datetime.timedelta(hours=24)):
			# Obtengo numero de dias a partir del todo
			number_days = total_time.days
			# Numero de veces promedio que debio irse al banio
			average_micturation_times = number_days*AVERAGE_MICTURITION_FREQ
			# Desviacion estandar
			deviation = 2*number_days
			# Rango de cantidad de idas al banio
			micturation_range = range(average_micturation_times - deviation, \
										average_micturation_times + deviation + 1)
			for s in sclass:
				eventos = s.get_mid_events()
				went_to_bathroom = [x for x in eventos if isinstance(x, MoveEvent) and \
									x.event == 'move-person-zone' and x.zone.name == 'bathroom']
				bathroom_times.append(len(went_to_bathroom))

				# 12. Dressing, veremos si el closet fue abierto alguna vez durante el
				# o los dias
				for e in eventos:
					if (isinstance(e, PropertyChangingEvent)):
						if (e.device.type_name == 'iCasa.DoorWindowSensor' and \
							e.changedProperty['value'] == 'true' and e.device.zones[0]['zone'].name == 'bedroom'):
							prev_event = [x for x in eventos if x.position == e.position - 1][0]
							if (isinstance(prev_event, MoveEvent)):
								# Abriendo puerta de cuarto y no closet, posible problema
								times_wd_opened.append(0)
							else:
								# Abri el closet
								executer = e.executer
								times_wd_opened.append(1)

			if (times_wd_opened):
				times_wd_opened = reduce((lambda x, y: x + y), times_wd_opened)
				if (times_wd_opened >= number_days):
					# Abri el closet al menos una vez al dia
					pass
				else:
					# No se ha cambiado
					elist.append({'position': None, 'executer': executer, 'error': 'Not changing clothes'})

			# Siguiendo con 10
			bathroom_times = reduce((lambda x, y: x + y), bathroom_times)
			# Comprobamos si la cantidad de veces en la sim esta ok
			if (bathroom_times in micturation_range):
				# Estoy dentro del rango
				pass
			else:				# Suponiendo existencia de solo una persona
				executer = [x for x in pclass][0]
				elist.append({'position': None, 'executer': executer.name, \
					'error': 'Irregular micturating time'})						

		# 11. Salir al menos una vez de casa
		# Se revisan las veces que salimos
		if (times_out):
			pass
			#times_out = reduce((lambda x, y: x + y), times_out)
			#print('Got out of house %d time(s)' % (times_out))
		else:
			if (total_time > datetime.timedelta(hours=24)):
				# Hay un problema
				executer = [x for x in pclass][0]
				elist.append({'position': None, 'executer': executer.name, 'error': 'Never going out'})

		# MAPEO DE ERRORES EN SIMULACION CON LAS CONSTANTES AGGIR

		for e in elist:
			for p in pclass:
				# Asocio errores con su executer
				if (e['executer'] == p):
					if (e['error'] == 'FloodSensor detected a problem'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Dificultad de movimiento
						p.aggir_const['TRANSFERS'] = False
						# Problemas con movimientos dentro de casa
						p.aggir_const['IN_MOVEMENTS'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'DimmerLight exceeded MAX time ON'):
						# Mal housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'BinaryLight exceeded MAX time ON'):
						# Mal housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'Heater exceeded MAX time ON'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'Cooler exceeded MAX time ON'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'Not getting out of room for much time'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Bad elimination
						p.aggir_const['ELIMINATION'] = False
						# Bad leisure
						p.aggir_const['LEISURE_ACTS'] = False
						# Bad alimentation
						p.aggir_const['ALIMENTATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'Possible accident in BATHROOM'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad transfers
						p.aggir_const['TRANSFERS'] = False
						# Bad houseleeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'Possible accident in LIVING ROOM'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad transfers
						p.aggir_const['TRANSFERS'] = False
						# Bad houseleeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'Possible accident in KITCHEN'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad transfers
						p.aggir_const['TRANSFERS'] = False
						# Bad houseleeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'Possible accident in HALLWAY'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad transfers
						p.aggir_const['TRANSFERS'] = False
						# Bad houseleeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'Heater on when no needed'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'Cooler on when no needed'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'HIGH CO CONCENTRATION'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'HIGH CO2 CONCENTRATION'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'Main door LET OPENED for much time'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'SIREN RINGING'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
					elif (e['error'] == 'Irregular micturating time'):
						# Bad elimination
						p.aggir_const['ELIMINATION'] = False
						# Bad toileting
						p.aggir_const['TOILETING'] = False
						# Bad alimentation
						p.aggir_const['ALIMENTATION'] = False
						# Bad transfers
						p.aggir_const['TRANSFERS'] = False
					elif (e['error'] == 'Never going out of house'):
						# Bad transfers
						p.aggir_const['TRANSFERS'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Bad shopping
						p.aggir_const['PURCHASES'] = False
						# Bad leisure
						p.aggir_const['LEISURE_ACTS'] = False
					elif (e['error'] == 'Not changing clothes'):
						# Bad dressing
						p.aggir_const['DRESSING'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad toileting
						p.aggir_const['TOILETING'] = False
					elif (e['error'] == 'Lights on at wrong time'):
						# Bad housekeeping
						p.aggir_const['HOUSEKEEPING'] = False
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'Wandering around at wrong time'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
					elif (e['error'] == 'Abandoning kitchen while cooking'):
						# Bad location
						p.aggir_const['LOCATION'] = False
						# Bad coherence
						p.aggir_const['COHERENCE'] = False
						# Bad houseleeping
						p.aggir_const['HOUSEKEEPING'] = False

		# Devolvemos respuesta
		for p in pclass:
			print('Inhabitant: %s\n' % (p))
			# Miramos si hay errores asociados al usuario
			errors_p = [x for x in elist if x['executer'] == p]
			if (errors_p):
				print('Detected problems: %s\n' % (len(errors_p)))
				no_repetition_elist = [x['error'] for x in errors_p]
				no_repetition_elist = list(set(no_repetition_elist))
				for e in no_repetition_elist:
					print('  - %s' % e)
				print('')
			else:
				print('Detected problems: %s\n' % (len(errors_p)))
			print('AGGIR variables value according to the analysis:\n')
			for var in p.aggir_const:
				print('%s: %s' % (var, p.aggir_const[var]))

# Llamado a funcion principal
if (__name__ == '__main__'):
	main(sys.argv)