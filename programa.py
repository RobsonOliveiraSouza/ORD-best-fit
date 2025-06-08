import sys
import io

IMPRIME_LED = True

"""
    UTILITARIOS
"""
def log_registro_removido(tam_registro: int, offset_registro: int):
    print(f'Registro removido! ({tam_registro} bytes)')
    print(f'Local: offset = {offset_registro} ({hex(offset_registro)})')
    print('')

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
    print(f'{registro} ({len(registro)} bytes)')
    print('')


"""
    OPERAÇÕES LED
"""
def ler_cabecalho_led(arq):
    arq.seek(0)
    ledCabecalho = arq.read(4)
    led = int.from_bytes(ledCabecalho, byteorder='big', signed=True)
    return led if led != 0 else -1

def escrever_cabecalho_led(arq, offset_novo_registro):
    arq.seek(0)
    arq.write(offset_novo_registro.to_bytes(4, byteorder='big', signed=True))

def remontar_led(led, arq, tamanho_novo_registro, offset_novo_registro):
    CABECA_LED = -1
    offset_anterior = CABECA_LED
    prox_offset = led

    while prox_offset != CABECA_LED:
        arq.seek(prox_offset)
        offset_anterior = prox_offset
        bytes_tamanho_registro_atual_led = arq.read(2)
        arq.read(1) # pula o asterisco
        bytes_prox_offset = arq.read(4)

        prox_offset = int.from_bytes(bytes_prox_offset, byteorder='big', signed=True) 
        tamanho_registro_atual_led = int.from_bytes(bytes_tamanho_registro_atual_led, byteorder='big', signed=True)

        if tamanho_novo_registro <= tamanho_registro_atual_led: # Caso o novo registro que será incluido na led seja menor que o registro atual da led
            # Registro anterior da led aponta para o novo registro inserido nela: 
            # ...    |       REGISTRO ANTERIOR LED        |                 NOVO REGISTRO ADICIONADO NA LED               |                  PROXIMO REGISTRO DA LED                 |   CONTINUAÇÃO LED   |
            # 
            # ... -> [offset: offset_anterior | tam: xxx] -> [offset: offset_novo_registro | tam: tamanho_novo_registro ] -> [offset: prox_offset | tam: tamanho_registro_atual_led] -> ...
            adicionar_novo_elemento_led(arq, offset_anterior, aponta_para=offset_novo_registro)
            adicionar_novo_elemento_led(arq, offset_novo_registro, aponta_para=prox_offset)
            log_registro_removido(tamanho_novo_registro, offset_novo_registro)
            return
    
    # Caso o novo registro adicionado na led seja maior que qualquer outro registro nela, é necessário adicionar no fim da LED, apontando pra cabeça dela
    adicionar_novo_elemento_led(arq, offset_anterior, aponta_para=offset_novo_registro)
    adicionar_novo_elemento_led(arq, offset_novo_registro, aponta_para=CABECA_LED)
    log_registro_removido(tamanho_novo_registro, offset_novo_registro)


def adicionar_novo_elemento_led(arq, offset_anterior, aponta_para):
    # Insere novo elemento no elemento anterior da led 
    arq.seek(offset_anterior + 3) # Desloca dos 2 bytes do tamanho do registro + '*'
    arq.write(aponta_para.to_bytes(4, byteorder='big', signed=True))

def ler_informacoes_registro_led(arq, offset_atual) -> tuple[int, int]:
    arq.seek(offset_atual)
    atualEspacoTam = int.from_bytes(arq.read(2), byteorder='big', signed=False)
    arq.read(1) #pula o "*"
    proxOffset = int.from_bytes(arq.read(4), byteorder='big', signed=True)
    return atualEspacoTam, proxOffset

def procurar_espaco_disponivel_led(cabeca_led: int, tamanho_registro: int, arq) -> tuple[bool, int, tuple[int, int]]: # Retorna o offset anterior, se o registro foi encontrado e o tamanho da celula
    (offset_anterior, prox_offset) = 0, cabeca_led

    while prox_offset != -1:
        arq.seek(prox_offset)
        bytes_espaco_disponivel_celula_led = arq.read(2)
        espaco_disponivel_celula_led = int.from_bytes(bytes_espaco_disponivel_celula_led, byteorder='big', signed=False)

        if espaco_disponivel_celula_led >= tamanho_registro:
            return (True, espaco_disponivel_celula_led, (offset_anterior, prox_offset))

        offset_anterior = prox_offset
        arq.read(1) # pula o '*'
        bytes_prox_offset = arq.read(4)
        prox_offset = int.from_bytes(bytes_prox_offset, byteorder='big', signed=True)


    return False, -1, (offset_anterior, prox_offset)

def percorrer_led(cabeca_led: int, arq):
    CABECA_LED = -1
    prox_offset = cabeca_led
    print('LED -> ', end='')
    while prox_offset != CABECA_LED:
        arq.seek(prox_offset)
        bytes_tam_celula_led = arq.read(2)
        arq.read(1) # Pula '*'
        bytes_prox_offset = arq.read(4)
        tamanho_celula_led = int.from_bytes(bytes_tam_celula_led, byteorder='big', signed=False)
        prox_offset = int.from_bytes(bytes_prox_offset, byteorder='big', signed=True)
        print(f'[offset: {prox_offset}, tam: {tamanho_celula_led}] -> ', end='')
    print(f'CABEÇA LED')

"""
    OPERAÇÕES REGISTRO
"""
def inserir_registro(registro: str, arq) -> None:
    arq.write(len(registro).to_bytes(2, byteorder='big', signed=False))
    arq.write(registro.encode('utf-8'))

"""
    OPERAÇÕES ARQUIVO
"""
def busca(chave, imprimir=True) -> int:
    try:
        with open("filmes.dat", 'rb') as arq:
            arq.read(4)
            bytes_tamanho_registro_atual = arq.read(2)  
            tamanho_registro_atual = int.from_bytes(bytes_tamanho_registro_atual, byteorder='big', signed=False)
            buffer = arq.read(tamanho_registro_atual)
            while buffer:
                registro = buffer.decode('utf-8', errors='replace')
                if '*' not in registro:
                    chave_registro = registro.split('|')[0]
                    if chave_registro == chave:
                        if imprimir:
                            log_busca(registro)
                        return arq.tell() - (tamanho_registro_atual + 2)
                bytes_tamanho_registro_atual = arq.read(2)           
                tamanho_registro_atual = int.from_bytes(bytes_tamanho_registro_atual, byteorder='big', signed=False)
                buffer = arq.read(tamanho_registro_atual)
            return -1
    except OSError as e:
        print(f"Erro ao abrir 'filmes.dat': {e}")
        return -1


def imprimir_led():
    try:
        with open("filmes.dat", 'r+b') as arq:
            CABECA_LED = -1
            cabeca_led = ler_cabecalho_led(arq)
            if cabeca_led == CABECA_LED: # LED vazia
                print(f'A LED está vazia.') 
                return
            percorrer_led(cabeca_led, arq)

    except IOError as e:
        print(f"Erro ao abrir o arquivo: {e}")

def insere(registro):
    try:
        with open("filmes.dat", 'r+b') as arq:
            cabeca_led = ler_cabecalho_led(arq)
            tamanho_registro = len(registro)
            (existe_espaco_disponivel_led, tamanho_espaco_disponivel, offsets) = procurar_espaco_disponivel_led(cabeca_led, tamanho_registro, arq)
            if existe_espaco_disponivel_led:
                # Fragmentação 
                inserir_em_espaco_led(registro, tamanho_espaco_disponivel, offsets, arq)
                return
            arq.seek(0, io.SEEK_END)
            arq.write(len(registro).to_bytes(2, byteorder='big', signed=False))
            arq.write(registro.encode('utf-8', errors='replace'))
            log_insercao(registro.split('|')[0], tamanho_registro)
    except OSError as e:
        print(f"Erro ao abrir 'filmes.dat': {e}")

def inserir_em_espaco_led(registro: str, tamanho_espaco_disponivel:int, offsets: tuple[int, int], arq) -> None:
    tamanho_registro_sem_padding = len(registro)
    fragmentacao = tamanho_espaco_disponivel - tamanho_registro_sem_padding
    if fragmentacao != 0:
        registro = registro[:-1] # Removendo ultimo '|'
        registro = registro.ljust(tamanho_espaco_disponivel - 1, '\0') # Colocando preenchimento
        registro += '|'

    (offset_anterior, offset_atual) = offsets
    arq.seek(offset_atual)
    arq.read(3) # 2 Bytes tam. reg. + '*'
    bytes_prox_offset = arq.read(4)
    prox_offset = int.from_bytes(bytes_prox_offset, byteorder='big', signed=True)
    prox_offset = 0 if prox_offset == -1 else prox_offset # Normalizando o próximo offset, caso ele seja a Cabeça da LED (-1)
    arq.seek(offset_anterior)
    if offset_anterior != 0: 
        arq.read(3) # 2 numeros do tamanho_registro + '*'
    arq.write(prox_offset.to_bytes(4, byteorder='big', signed=True))
    arq.seek(offset_atual)
    arq.write(len(registro).to_bytes(2, byteorder='big', signed=False))
    arq.write(registro.encode('utf-8', errors='replace'))
    log_insercao(registro.split('|')[0], tamanho_registro_sem_padding, offset_atual, fragmentacao)

def remove(chave):
    try:
        offset = busca(chave, imprimir=False)
        CABECA_LED = -1
        print(f'Remoção do registro de chave "{chave}"')
        if offset == -1:
            print('Erro: registro não encontrado!\n')
            return
        with open("filmes.dat", 'r+b') as arq:
            led = ler_cabecalho_led(arq)

            arq.seek(offset)
            tamanho_registro_as_bytes = arq.read(2)

            if not tamanho_registro_as_bytes:
                print(f'Não foi possível obter o tamanho do registro que será deletado.')

            tamanho_registro = int.from_bytes(tamanho_registro_as_bytes, byteorder='big')
            arq.write(b'*') # Coloca o '*' marcando como removido
            tamanho_novo_registro_deletado = tamanho_registro
            offset_novo_registro_deletado = offset

            if led == CABECA_LED: # Caso mais simples: Não foi removido nenhum registro da led.
                escrever_cabecalho_led(arq, offset_novo_registro_deletado)
                adicionar_novo_elemento_led(arq, offset_anterior=offset_novo_registro_deletado, aponta_para=CABECA_LED)
                log_registro_removido(tamanho_novo_registro_deletado, offset_novo_registro_deletado)
                return

            # Vai ter que adicionar o novo registro na led
            remontar_led(led, arq, tamanho_novo_registro_deletado, offset_novo_registro_deletado)
    except OSError as e:
        print(f"Erro ao abrir 'filmes.dat': {e}")


def compactar_arquivo():
    print(f'Iniciando compactação do arquivo filmes.dat...')
    try:
        with open("filmes.dat", 'r+b') as arq:
            with open("filmes_compactado.dat", 'w+b') as arq_compactado:
                arq.read(4)
                arq_compactado.write(int(0).to_bytes(4, byteorder='big', signed=True))
                bytes_tamanho_registro_atual = arq.read(2)  
                tamanho_registro_atual = int.from_bytes(bytes_tamanho_registro_atual, byteorder='big', signed=False)
                buffer = arq.read(tamanho_registro_atual)
                while buffer:
                    registro = buffer.decode('utf-8', errors='replace')
                    if '*' not in registro:
                        arq_compactado.write(tamanho_registro_atual.to_bytes(2, byteorder='big', signed=False))
                        arq_compactado.write(registro.encode(encoding='utf-8', errors='replace'))
                    bytes_tamanho_registro_atual = arq.read(2)           
                    tamanho_registro_atual = int.from_bytes(bytes_tamanho_registro_atual, byteorder='big', signed=False)
                    buffer = arq.read(tamanho_registro_atual)
                print(f'Compactação finalizada! O arquivo compactado se chama "filmes_compactado.dat"')
    except OSError as e:
        print(f'Erro ao abrir "filmes.dat": {e}')

def arquivo(nomeArq):
    try:
        with open(nomeArq, "r") as arq:
            linhas = arq.readlines()
            for linha in linhas:
                linha = linha.strip()
                if linha:
                    operacao = linha[0]
                    if len(linha.split()) > 1:
                        chave = linha.split()[1]
                        chave = chave.split('|')[0]
                        if operacao == "b":
                            busca(chave)
                        elif operacao == "r":
                            remove(chave)
                        elif operacao == "i":
                            indiceEspaco = linha.index(' ')
                            registro = linha[indiceEspaco + 1:]
                            insere(registro)
                        else:
                            print(f"Operação '{operacao}' não reconhecida.")
                    else:
                        print("Linha mal formatada ou faltando chave: ", linha)
    except OSError as e:
        print(f"Erro ao abrir '{nomeArq}': {e}")

nomeArq = "operacoes.txt"

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == '-e':
        nomeArq = sys.argv[2]
        arquivo(nomeArq)
    elif len(sys.argv) == 2 and sys.argv[1] == '-p':
        imprimir_led()
    elif len(sys.argv) == 2 and sys.argv[1] == '-c':
        compactar_arquivo()
    else:
        print("Uso: python programa.py -e operacoes.txt")
        print("Ou: python programa.py -p")

