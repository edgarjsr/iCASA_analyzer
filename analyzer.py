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

# Aniadir en este bloque

#################################
# Definicion de variables AGGIR #
#################################

# NOTA: La variables tienen tres valores posibles de
# acuerdo al nivel de dependencia del sujeto, asi:

# A: dependencia completa
# B: dependencia parcial
# C: independencia completa

# Variables discriminatorias, por defecto tendran valor 'A'
COHERENCE = 'A'
LOCATION = 'A'
TOILETING = 'A'
DRESSING = 'A'
ALIMENTATION = 'A'
ELIMINATION = 'A'
TRANSFERS = 'A'
IN_MOVEMENTS = 'A'
OUT_MOVEMENTS = 'A'
DIST_COMMUNICATION = 'A'

# Variables ilustrativas, por defecto tendran valor 'A'
MANAGEMENT = 'A'
COOKING = 'A'
HOUSEKEEPING = 'A'
TRANSPORTATION = 'A'
PURCHASES = 'A'
MEDICAL_TREATMENT = 'A'
LEISURE_ACTS = 'A'

#################################
# Funciones utiles              #
#################################

# Funcion varsInList
# Retorna true si el key 'key' esta presente en algun elemento
# de la lista 'list'.
# @args
#    key: clave a buscar
#    list: lista

def varsInList(key, list):
	results = []
	for e in list:
		results.append(key in e)
	return (True in results)

# Funcion numerador
# Numera las acciones en el xml
# @args
#    root: raiz del xml

def numerador(root):
	i = 0
	for child in root:
		child.set('orden', i)
		i += 1

# Funcion update_dict_zones
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

# Funcion event_generator
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

# Funcion positionOrdering
# Funciona de key para el sort()
# @args
#    event: evento de la lista de eventos

def positionOrdering(event):
	return event.position


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
class Person:

	# Inicializador
	def __init__(self, name, type_name, zones):
		self.name = name
		self.type_name = type_name
		self.zones = zones

	def __str__(self):
		return '{self.name} de tipo {self.type_name}'.format(self=self)

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

# Clase VarChangingEvent - Subclase de Event
# Modela cambios de variables en zonas
#
# @attrs
#    change: dict de variable/valor modificado
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
	# Si pasaron menos de dos argumentos
	if (len(argv) < 2):
		print('Usage: analyzer.py input_file.bhv')
		sys.exit(1)
	# Si pasaron mas de dos argumentos
	elif (len(argv) > 2):
		print('Usage: analyzer.py input_file.bhv')
		sys.exit(2)
	# Pasaron los dos argumentos necesarios
	else:
		# Genero ElementTree a partir del archivo
		simulacion = ET.parse(argv[1])
		behavior = simulacion.getroot()

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
			print('No starting time given.')

		# Numerando acciones
		numerador(behavior)

		# Listas para almacenar objetos de cada tipo descrito
		zones = []
		devices = []
		people = []
		delay = []

		# Lista de dics para zones, devices y people
		zlist = []
		dlist = []
		plist = []
		tlist = []
		slist = []

		# Listas de instancias de clases para cada elemento
		pclass = []
		dclass = []
		zclass = []
		eclass = []
		sclass = []

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
			else:
				pass

		# Obtengo variables asociadas a cada zona
		if (len(zones) > 0):
			for zone in zones:
				zdic = {}
				zdic['zone'] = zone.attrib['id']
				zdic['orden'] = zone.attrib['orden']
				for child in behavior:
					if (child.tag == 'add-zone-variable' and child.attrib['zoneId'] == zone.attrib['id']):
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
						if (child.tag == 'modify-zone-variable' and child.attrib['zoneId'] == z['zone']):
							tmp = z['vars']
							tmp[child.attrib['variable']] = child.attrib['value']
							z['vars'] = tmp
			# Si no hay, skip
			else:
				pass

		# TENGO TODO DE LAS ZONAS

		if (len(devices) > 0):
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
							tmp.append({'orden': child.attrib['orden'], 'zone': child.attrib['zoneId']})
							ddic['zone'] = tmp
						# Creo la nueva lista
						else:
							ddic['zone'] = [{'orden': child.attrib['orden'], 'zone': child.attrib['zoneId']}]
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

		if (len(people) > 0):
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
							tmp.append({'orden': child.attrib['orden'], 'zone': child.attrib['zoneId']})
							pdic['zone'] = tmp
						# Creo dic de zonas en otro caso
						else:
							pdic['zone'] = [{'orden': child.attrib['orden'], 'zone': child.attrib['zoneId']}]
				plist.append(pdic)

		# TENGO A LAS PERSONAS Y SUS ZONAS CORRESPONDIENTES

		# Obtengo estructuras de tiempo
		if (len(delay) > 0):
			for d in delay:
				tdict = {}
				tdict['expr'] = d.tag
				tdict['orden'] = d.attrib['orden']
				tdict['value'] = d.attrib['value']
				tdict['unit'] = d.attrib['unit']
				tlist.append(tdict)

		# TENGO TODOS LOS DELAY DESGLOSADOS, ES UN EVENT

		if (len(zlist) > 0):
			# Generando instancias de clases para zonas
			for elem in zlist:
				zclass.append(Zone(elem['orden'], elem['zone'], elem['vars']))

			# Actualizando zonas en dict de devices
			update_dict_zones(dlist, zclass)

			# Actualizando zonas en dict de people
			update_dict_zones(plist, zclass)

		if (len(dlist) > 0):
			# Generando instancias de clases para dispositivos
			for elem in dlist:
				try:
					dclass.append(Device(elem['orden'], elem['device'], elem['type'], elem['events'], elem['zone']))
				except:
					dclass.append(Device(elem['orden'], elem['device'], elem['type'], [], elem['zone']))

		if (len(plist) > 0):
			# Generando instancias de clases para personas
			for elem in plist:
				pclass.append(Person(elem['name'], elem['type'], elem['zone']))

		# Generando instancias de eventos

		# CASO 1: move-device-zone

		# No hay personas generadas
		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'move-device-zone'):
					tmp = [c for c in behavior if c.attrib['orden'] < child.attrib['orden']]
					if (len(tmp) > 0):
						# Caso setup
						if (tmp[len(tmp) - 1].tag == 'create-device'):
							pass
						# Caso movimiento de persona previo
						elif (tmp[len(tmp) - 1].tag == 'move-person-zone'):
							executer = [p for p in pclass if p.name == tmp[len(tmp) - 1].attrib['personId']][0]
							eclass.append(Event(executer, child.attrib['orden'], child.tag))
						else:
							pass

		# CASO 2: modify-zone-variable

		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'modify-zone-variable'):
					tmp = [c for c in behavior if c.attrib['orden'] < child.attrib['orden']]
					if (len(tmp) > 0):
						# Caso setup
						if (tmp[len(tmp) - 1].tag == 'add-zone-variable'):
							pass
						# Casos de cambio por movimiento de persona
						elif (tmp[len(tmp) - 1].tag == 'move-person-zone'):
							executer = [p for p in pclass if p.name == tmp[len(tmp) - 1].attrib['personId']][0]
							dictionary = {'variable': child.attrib['variable'], 'value': child.attrib['value']}
							eclass.append(VarChangingEvent(executer, child.attrib['orden'], child.tag, \
								dictionary))
						elif (tmp[len(tmp) - 1].tag == 'move-device-zone' \
							and tmp[len(tmp) - 2].tag == 'move-person-zone'):
							executer = [p for p in pclass if p.name == tmp[len(tmp) - 2].attrib['personId']][0]
							dictionary = {'variable': child.attrib['variable'], 'value': child.attrib['value']}
							eclass.append(VarChangingEvent(executer, child.attrib['orden'], child.tag, \
								dictionary))
						else:
							pass

		# CASO 3: set-device-property

		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'set-device-property'):
					tmp = [x for x in behavior if x.attrib['orden'] < child.attrib['orden']]
					if (len(tmp) > 0):
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
							# Crearemos, a modo de test, clases con executer None
							eclass.append(PropertyChangingEvent(None, child.attrib['orden'], \
								device, changes))

		# Si hay una sola persona, es el unico executer posible
		if (len(people) == 1):
			executer = pclass[0]
			for elem in eclass:
				if (isinstance(elem, PropertyChangingEvent)):
					elem.executer = executer

		# PENDIENTE: considerar cuando hay mas de una persona

		# CASO 4: fault device

		if (len(people) == 0):
			pass
		else:
			for child in behavior:
				if (child.tag == 'fault-device'):
					dev = child.attrib['deviceId']
					try:
						# Ultima ubicacion del device
						place = [x.attrib['zoneId'] for x in behavior if \
						x.attrib['orden'] < child.attrib['orden'] and x.tag == 'move-device-zone' \
						and x.attrib['deviceId'] == dev][0]
						place = [x for x in zclass if x.name == place][0]
						tmp = [x for x in behavior if x.attrib['orden'] < child.attrib['orden'] \
						and x.tag == 'move-person-zone' and x.attrib['zoneId'] == place.name]
						# Si hay eventos previos a la accion
						if (len(tmp) > 0):
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
					eclass.append(Event(executer, child.attrib['orden'], child.tag))

		# CASO x: delay - DEBE IR AL FINAL

		# Si hay acciones en lista de events, aniado a la lista
		if (len(eclass) > 0):
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

		#for child in behavior:
		#	print('Veamos, %s con orden %s\n'  % (child.tag, child.attrib['orden']))

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
	
		for zone in zones:
			print("Zona: %s\n" % (zone.attrib['id']))

# Llamado a funcion principal
if (__name__ == '__main__'):
	main(sys.argv)