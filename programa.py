import sys
import io

IMPRIME_LED = True

CABECALHO_LED_SIZE = 4
TAM_REGISTRO_SIZE = 2
REMOVIDO_FLAG = b'*'
CABECA_LED = -1


# Utilitários

def log_registro_removido(tam_registro: int, offset_registro: int):
    print(f'Registro removido! ({tam_registro} bytes)')
    print(f'Local: offset = {offset_registro} ({hex(offset_registro)})\n')

def log_insercao(id_registro: int, tam_registro: int, offset: int = 0, fragmentacao: int = 0):
    print(f'Inserção do registro de chave "{id_registro}" ({tam_registro} bytes)')
    if fragmentacao == 0:
        print('Local: Fim do arquivo')
    else:
        print(f'Espaço reutilizado: {fragmentacao} bytes')
        print(f'Local: offset = {offset} bytes ({hex(offset)})')
    print('')

def log_busca(registro: str):
    id_registro = registro.split('|')[0]
    print(f'Busca pelo registro de chave "{id_registro}"')
    print(f'{registro} ({len(registro)} bytes)\n')


# LED

def ler_cabecalho_led(arq):
    arq.seek(0)
    return int.from_bytes(arq.read(4), byteorder='big', signed=True)

def escrever_cabecalho_led(arq, offset):
    arq.seek(0)
    arq.write(offset.to_bytes(4, byteorder='big', signed=True))

def adicionar_novo_elemento_led(arq, offset_anterior, aponta_para):
    arq.seek(offset_anterior + 3)
    arq.write(aponta_para.to_bytes(4, byteorder='big', signed=True))

def remontar_led(led, arq, tam_reg, offset_novo):
    offset_anterior = -1
    prox = led
    while prox != -1:
        arq.seek(prox)
        tam_atual = int.from_bytes(arq.read(2), 'big')
        arq.read(1)
        prox_next = int.from_bytes(arq.read(4), 'big', signed=True)

        if tam_reg <= tam_atual:
            if offset_anterior == -1:
                escrever_cabecalho_led(arq, offset_novo)
            else:
                adicionar_novo_elemento_led(arq, offset_anterior, offset_novo)

            adicionar_novo_elemento_led(arq, offset_novo, prox)
            log_registro_removido(tam_reg, offset_novo)
            return

        offset_anterior = prox
        prox = prox_next

    if offset_anterior != -1:
        adicionar_novo_elemento_led(arq, offset_anterior, offset_novo)
        adicionar_novo_elemento_led(arq, offset_novo, -1)
        log_registro_removido(tam_reg, offset_novo)


def percorrer_led(cabeca, arq):
    prox = cabeca
    print('LED -> ', end='')
    while prox != -1:
        arq.seek(prox)
        tam = int.from_bytes(arq.read(2), 'big')
        arq.read(1)
        prox_next = int.from_bytes(arq.read(4), 'big', signed=True)
        print(f'[{prox}({tam}) -> {prox_next}] -> ', end='')
        prox = prox_next
    print('FIM')


# Arquivo

def busca(chave, imprimir=True):
    try:
        with open('filmes.dat', 'rb') as arq:
            arq.seek(4)
            while True:
                offset = arq.tell()
                tam_bytes = arq.read(2)
                if not tam_bytes or len(tam_bytes) < 2:
                    break
                tam = int.from_bytes(tam_bytes, 'big')
                data = arq.read(tam)
                if data[:1] == REMOVIDO_FLAG:
                    continue
                registro = data.decode('utf-8', 'replace')
                if registro.split('|')[0] == chave:
                    if imprimir:
                        log_busca(registro)
                    return offset
        if imprimir:
            print(f'Jogo com identificador {chave} não encontrado.\n')
        return -1
    except OSError as e:
        print(f'Erro ao abrir "filmes.dat": {e}')
        return -1

def imprimir_led():
    try:
        with open('filmes.dat', 'rb') as arq:
            cabeca = ler_cabecalho_led(arq)
            if cabeca == -1:
                print('LED está vazia.')
                return
            percorrer_led(cabeca, arq)
    except OSError as e:
        print(f'Erro ao abrir o arquivo: {e}')


def inserir_em_espaco_led(registro, tam_disp, offsets, arq):
    reg_bytes = registro.encode('utf-8')
    tam_reg = len(reg_bytes)
    fragmentacao = tam_disp - tam_reg
    if fragmentacao:
        reg_bytes = reg_bytes.ljust(tam_disp, b'\0')

    offset_ant, offset_disp = offsets
    arq.seek(offset_disp + 3)
    prox = int.from_bytes(arq.read(4), 'big', signed=True)

    arq.seek(offset_disp)
    arq.write(tam_disp.to_bytes(2, 'big'))
    arq.write(reg_bytes)

    if offset_ant == 0:
        escrever_cabecalho_led(arq, prox)
    else:
        arq.seek(offset_ant + 3)
        arq.write(prox.to_bytes(4, 'big', signed=True))

    log_insercao(registro.split('|')[0], tam_reg, offset_disp, fragmentacao)


def procurar_espaco_disponivel_led(cabeca, tam_reg, arq):
    offset_ant = 0
    prox = cabeca
    while prox != -1:
        arq.seek(prox)
        tam = int.from_bytes(arq.read(2), 'big')
        arq.read(1)
        prox_next = int.from_bytes(arq.read(4), 'big', signed=True)
        if tam >= tam_reg:
            return True, tam, (offset_ant, prox)
        offset_ant = prox
        prox = prox_next
    return False, -1, (offset_ant, prox)


def insere(registro):
    try:
        with open('filmes.dat', 'r+b') as arq:
            cabeca = ler_cabecalho_led(arq)
            tam_reg = len(registro.encode('utf-8'))
            encontrado, tam_disp, offsets = procurar_espaco_disponivel_led(cabeca, tam_reg, arq)
            if encontrado:
                inserir_em_espaco_led(registro, tam_disp, offsets, arq)
            else:
                arq.seek(0, io.SEEK_END)
                arq.write(tam_reg.to_bytes(2, 'big'))
                arq.write(registro.encode('utf-8'))
                log_insercao(registro.split('|')[0], tam_reg)
    except OSError as e:
        print(f'Erro ao abrir "filmes.dat": {e}')


def remove(chave):
    try:
        offset = busca(chave, imprimir=False)
        print(f'Remoção do registro de chave "{chave}"')
        if offset == -1:
            print('Erro: registro não encontrado!\n')
            return
        with open('filmes.dat', 'r+b') as arq:
            arq.seek(offset)
            tam_bytes = arq.read(2)
            tam = int.from_bytes(tam_bytes, 'big')

            arq.seek(offset + 2)
            arq.write(REMOVIDO_FLAG)
            arq.write(b'\0' * (tam - 1))

            cabeca = ler_cabecalho_led(arq)
            escrever_cabecalho_led(arq, offset)
            arq.seek(offset + 3)
            arq.write(cabeca.to_bytes(4, 'big', signed=True))
            log_registro_removido(tam, offset)
    except OSError as e:
        print(f'Erro ao abrir "filmes.dat": {e}')


def arquivo(nomeArq):
    try:
        with open(nomeArq, 'r') as arq:
            for linha in arq:
                linha = linha.strip()
                if not linha: continue
                oper = linha[0]
                dados = linha[2:]
                if oper == 'b':
                    busca(dados)
                elif oper == 'r':
                    remove(dados)
                elif oper == 'i':
                    insere(dados)
    except OSError as e:
        print(f'Erro ao abrir "{nomeArq}": {e}')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '-e':
        arquivo(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == '-p':
        imprimir_led()
    else:
        print("Uso: python programa.py -e operacoes.txt")
        print("Ou: python programa.py -p")
