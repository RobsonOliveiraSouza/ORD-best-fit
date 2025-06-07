import sys
import io

IMPRIME_LED = True

"""
    UTILITARIOS
"""
def log_registro_removido(tam_registro: int, offset_registro: int):
    print(f'''Registro removido! ({tam_registro} bytes)
            Local: offset = {offset_registro} bytes ({tam_registro.to_bytes(2, byteorder='little')})''')

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

def adicionar_novo_registro_deletado_led(led, arq, tamanho_novo_registro, offset_novo_registro):

    CABECA_LED = -1
    offset_anterior = CABECA_LED
    prox_offset = ler_cabecalho_led(arq) 

    while prox_offset != CABECA_LED:
        arq.seek(prox_offset)
        offset_anterior = prox_offset
        bytes_tamanho_registro_atual_led = arq.read(2)
        arq.seek(1) # pula o asterisco
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
    atualEspacoTam = int.from_bytes(arq.read(2), byteorder='big')
    arq.read(1) #pula o "*"
    proxOffset = int.from_bytes(arq.read(4), byteorder='big', signed=True)
    return atualEspacoTam, proxOffset

def procurar_espaco_disponivel_led(cabeca_led: int, tamanho_registro: int, arq) -> tuple[bool, int, tuple[int, int]]: # Retorna o offset anterior, se o registro foi encontrado e o tamanho da celula
    offset_anterior = -1
    (offset_atual, prox_offset) = cabeca_led, -1 
    while offset_atual != -1:
        arq.seek(offset_atual)
        (tamanho_celula_led, prox_offset) = ler_informacoes_registro_led(arq, offset_atual)
        if tamanho_celula_led >= tamanho_registro:
            return True, tamanho_celula_led, (offset_anterior, offset_atual)
        offset_anterior = offset_atual
        offset_atual = prox_offset
    arq.seek(0, io.SEEK_END) # Caso não encontre espaço disponível, adicionar registro no fim do arquivo 
    return False, -1, (offset_anterior, offset_atual)


"""
    OPERAÇÕES REGISTRO
"""
def inserir_registro(tamanho_registro: int, registro: str, arq) -> None:
    arq.write(tamanho_registro.to_bytes(2, byteorder='big', signed=False))
    arq.write(registro.encode('utf-8'))

"""
    OPERAÇÕES ARQUIVO
"""
def leia_reg(arq) -> tuple[str, int]:
    try:
        tam_bytes = arq.read(2)
        if len(tam_bytes) < 2:
            return '', 0
        tam = int.from_bytes(tam_bytes, byteorder='big')
        if tam > 0:
            buffer = arq.read(tam)
            return buffer.decode('utf-8', errors='replace'), tam
    except OSError as e:
        print(f'Erro leia_reg: {e}')
    return '', 0

def busca(chave, imprimir=True) -> int:
    try:
        with open("filmes.dat", 'rb') as arq:
            arq.read(4)
            achou = False
            buffer, tam = leia_reg(arq)
            offset = 4
            if imprimir:
                print(f'Busca pelo registro de "{chave}"')
            while buffer and not achou:
                key = buffer.split('|')[0]
                if chave == key:
                    achou = True
                    if imprimir:
                        print(f"{buffer} ({tam} bytes)\n")
                else:
                    offset += tam + 2
                    buffer, tam = leia_reg(arq)
            if not achou:
                if imprimir:
                    print(f'Jogo com identificador {chave} não encontrado.\n')
                return -1
            return offset
    except OSError as e:
        print(f"Erro ao abrir 'filmes.dat': {e}")

def imprimeLED(imprimir=True):
    try:
        with open("filmes.dat", 'r+b') as arq:
            arq.seek(0)
            ledCabecalho = arq.read(4)
            led = int.from_bytes(ledCabecalho, byteorder='big', signed=True)
            if led == -1:
                if imprimir:
                    print("\nLED está vazia.\n")
                return
            cont = 0
            print("\nLED -> ", end='')
            while led != -1:
                arq.seek(led)
                espaco = int.from_bytes(arq.read(2), byteorder='big')
                arq.read(1)
                proxOffset = int.from_bytes(arq.read(4), byteorder='big', signed=True)
                if imprimir:
                    print(f"[offset: {led}, tam: {espaco}] -> ", end='')
                led = proxOffset
                cont += 1
            if imprimir:
                print("[offset: -1]")
                print(f"Total: {cont} espaços disponíveis\n")
    except IOError as e:
        print(f"Erro ao abrir o arquivo: {e}")

def insere(registro):
    try:
        with open("filmes.dat", 'r+b') as arq:
            id_registro = registro.split('|')[0]
            cabeca_led = ler_cabecalho_led(arq)
            tamanho_registro = len(registro)
            print(f'Inserindo registro {id_registro} ({tamanho_registro} bytes)')
            #tuple[bool, int, int, int] 
            (existe_espaco_disponivel_led, tamanho_espaco_disponivel, offsets) = procurar_espaco_disponivel_led(cabeca_led, tamanho_registro, arq)
            if existe_espaco_disponivel_led:
                print(f'Espaço disponível encontrado! {tamanho_espaco_disponivel} bytes')
                print(f'Fragmentacao: {tamanho_espaco_disponivel - tamanho_registro} bytes')
                inserir_em_espaco_led(registro, tamanho_espaco_disponivel, offsets, arq)
                # Fragmentação 
                return
            print(f'Não foi encontrado espaço disponível na led...')
            # Assumindo que o ponteiro do arquivo esteja no fim do arquivo:
            inserir_registro(tamanho_registro, registro, arq)
            print(f'Registro {id_registro} inserido no final do arquivo com {tamanho_registro} bytes. \n')
    except OSError as e:
        print(f"Erro ao abrir 'filmes.dat': {e}")

def inserir_em_espaco_led(registro: str, tamanho_espaco_disponivel:int, offsets: tuple[int, int], arq) -> None:
    tamanho_registro_sem_padding = len(registro)
    fragmentacao = tamanho_espaco_disponivel - tamanho_registro_sem_padding
    mensagem_fragmentacao = ''
    if fragmentacao != 0:
        mensagem_fragmentacao = f' (+ {fragmentacao} bytes p/ evitar fragmentação)'
        print(f'Fragmentacao encontrada: {fragmentacao} bytes')
        registro.rjust(tamanho_espaco_disponivel, '\0')
    inserir_registro(len(registro), registro, arq)
    (offset_anterior, prox_offset) = offsets
    arq.seek(offset_anterior + 3) # 2 numeros do tamanho_registro + '*'
    arq.write(prox_offset.to_bytes(4, byteorder='big', signed=True))
    print(f'Registro inserido! {str(tamanho_registro_sem_padding)+mensagem_fragmentacao}')

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
            print(f'Valor cabeçalho led: {led}')

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
            adicionar_novo_registro_deletado_led(led, arq, tamanho_novo_registro_deletado, offset_novo_registro_deletado)
    except OSError as e:
        print(f"Erro ao abrir 'filmes.dat': {e}")

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
        imprimeLED(imprimir=True)
    else:
        print("Uso: python programa.py -e operacoes.txt")
        print("Ou: python programa.py -p")

