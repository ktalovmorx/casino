#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#https://cx-freeze.readthedocs.io/en/latest/setup_script.html
__author__ = 'Jose Ernesto Morales Ventura'
__date__ = '18/05/2023'
__proyect__ = 'Casino'
__description__ = 'Simulador de estrategia gale 666 en casino'

import random
from collections import Counter

class Cashier(object):
    pass


class Azar(object):
    """
    Clase de aleatoreidad
    """

    def __init__(self):
        #-- Escoge una semilla aleaotoria
        random.seed(random.randint(1, 100))

    def generate_numbers(self, table:list, nth:int, zero_fix:bool, _form:str) -> list:
        """
        form : dozens, six, street, pair, straight
        Genera nth numeros aleatorios de la tabla exceptuando los numeros 0, 00, 1, 18, 21 y 36
        """
        dozens = [[x for x in range(1,13)],[x for x in range(13,25)],[x for x in range(25,37)]]
        streets = [[1,2,3],[4,5,6],[7,8,9],[10,11,12],[13,14,15],[16,17,18],
                   [19,20,21],[22,23,24],[25,26,27],[28,29,30],[31,32,33],[34,35,36]
                   ]
        pairs = [[1,4],[2,5],[3,6],[7,10],[8,11],[9,12],[13,16],[14,17],
                 [15,18],[19,22],[20,23],[21,24],[25,28],[26,29],[27,30],
                 [31,34],[32,35],[33,36]]
        lst_out = []
        if _form == 'straights':
            nth=nth
            zero_fix = False
        elif _form == 'pairs':
            nth = 2
            zero_fix = False
        elif _form == 'streets':
            nth = 3
            zero_fix = False
        elif _form == 'sixs':
            nth=6
            zero_fix = False
        elif _form == 'dozens':
            nth=12
            zero_fix = False
        else:
            nth=nth
            zero_fix = False

        while True:
            if len(lst_out) == nth:
                break
            if _form == 'straight':
                nth = nth
                rand_number = random.choice(table)
                #-- Evita dar estos numeros
                if rand_number in ('0', '00', '1', '18', '21', '36'):
                    continue
                if not rand_number in lst_out:
                    lst_out.append(rand_number)
                    if len(lst_out) == nth:
                        break
            elif _form == 'pairs':
                rand_numbers = random.choice(pairs)
                for r in rand_numbers:
                    #- Evita dar los pares que tienen estos numeros
                    if r in ('0', '00', '1', '18', '21', '36'):
                        continue
                    if not r in lst_out:
                        lst_out.append(r)
                        if len(lst_out) == nth:
                            break
            elif _form == 'streets':
                rand_numbers = random.choice(streets)
                for r in rand_numbers:
                    #- Evita dar las calles que tienen estos numeros
                    if r in ('0', '00', '1', '18', '21', '36'):
                        continue
                    if not r in lst_out:
                        lst_out.append(r)
                        if len(lst_out) == nth:
                            break
            elif _form == 'sixs':
                #-- Generamos SEXTAS pero que no tienen que estar unidas necesariamente
                rand_number = random.choice(streets)
                for r in rand_number:
                    _exist = False
                    for x in ('0', '00', '1', '18', '21', '36'):
                        if x in r:
                            _exist=True
                            break
                    if _exist:
                        continue
                    else:
                        for x in rand_number:
                            lst_out.append(x)
                    if len(lst_out) == nth:
                        break
            elif _form == 'dozens':
                #-- Generamos DOCENAS pero que no tienen que estar unidas necesariamente
                rand_number = random.choice(dozens)
                for r in rand_number:
                    lst_out.append(r)
                    if len(lst_out) == nth:
                        break
            else:
                None
        if zero_fix:
            return ['0'] + lst_out[1:]
        else:
            return lst_out

    def generate_number(self, table) -> str:
        return str(random.choice(table))


class Roulette(Azar):


    def __init__(self, roulette_type):
        self.table = self.__generate_table(roulette_type)
        self.roulette_type = roulette_type

    def __generate_table(self, roulette_type) -> list:
        if roulette_type == 'EU':
            return self.__generate_eu()
        else:
            return self.__generate_am()

    def __generate_eu(self) -> list:
        return ['0'] + [str(x) for x in range(1, 37)]

    def __generate_am(self) -> list:
        return ['00'] + self.__generate_eu()

    def spin(self) -> str:
        rand_number = self.generate_number(self.table)
        return rand_number


class Dealer(object):


    def __init__(self, name, silent):
        self.name = name
        self.silent = silent

    def set_player(self, player) -> None:
        self.player = player
        self.roulette = player.roulette
        print(f'Welcome {player.name}, please place your bets...')

    def spin(self) -> None:
        """
        Retorna un numero aleatorio de la ruleta
        """
        if not self.silent:
            print('Thanks, no more bets')
        self.ball_position = self.roulette.spin()

    def review_and_pay(self) -> bool:
        """
        Verifica si la bola callo en uno de los NTH numeros que el usuario dejo aperturados
        """
        state = self.ball_position in self.player.empty_numbers
        if state:
            state = 'Loss'
        else:
            state = 'Win'
        if not self.silent:
            print(f'{self.player.empty_numbers} \t {self.ball_position} \t {state}')
        return state


class Player(object):


    def __init__(self, name, silent = True):
        self.name = name
        self.silent = silent
        self.lucky = Azar()

    def sitdown_roulette(self, roulette_type, open_numbers) -> None:
        self.open_numbers = open_numbers
        self.roulette = Roulette(roulette_type)

    def set_empty_numbers(self, zero_fix=False, _form='straight') -> None:
        """
        Selecciona 2 numeros aleatorios sin repeticion
        """
        self.empty_numbers = self.lucky.generate_numbers(self.roulette.table, self.open_numbers, zero_fix, _form)
        if not self.silent:
            print('I\'m ready')

def calculate_secs(plays, values):
    counter = 0
    for i in range(len(plays) - len(values) + 1):
        if plays[i:i+len(values)] == values:
            counter += 1
    print(f'PLAYS:{len(plays)}')
    print(f'REPS:{counter}')

def calculate_accuracy(plays) -> float:
    acc = plays.count('Win')*100.0/float(len(plays))
    print(f'ACCURACY:{acc}')

def more_repeated(lista):
    contador = Counter(lista)
    valor_mas_repetido = contador.most_common(1)[0][0]
    resultado = {valor: contador[valor] for valor in contador}
    resultado['max_rep'] = contador[valor_mas_repetido]
    return resultado

def probability_test():
    dealer = Dealer('Clara', True)
    p1 = Player('Jose', True)
    p1.sitdown_roulette(roulette_type='EU', open_numbers=4)
    dealer.set_player(p1)

    plays = []
    moments = []
    total_chances = 3
    repeat = 100
    max_plays = 10
    count = 0
    for y in range(repeat):
        for x in range(max_plays):
            count += 1
            p1.set_empty_numbers(zero_fix=True, _form='straight')
            dealer.spin()
            result = dealer.review_and_pay()
            if result == 'Loss':
                moments.append(count)
            plays.append(result)
            if count == 10:
                count = 0
    calculate_accuracy(plays)
    calculate_secs(plays, ['Loss' for x in range(total_chances)])
    
    print('OCCURS:', more_repeated(moments), sep='\n')
    del p1
    del dealer

if __name__ == '__main__':
    #probability_test()
    dealer = Dealer('Clara', silent=False)
    p1 = Player('Jose', silent=True)
    p1.sitdown_roulette(roulette_type='EU', open_numbers=3)
    dealer.set_player(p1)
    p1.set_empty_numbers(zero_fix=True, _form='dozens')
    dealer.spin()
    result = dealer.review_and_pay()
    print(result)
