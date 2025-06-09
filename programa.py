import sys
import io

IMPRIME_LED = True      # Flag para imprimir a LED ao inserir registros

CABECALHO_LED_SIZE = 4
TAM_REGISTRO_SIZE = 2
REMOVIDO_FLAG = b'*'    # Flag que indica que o registro foi removido
CABECA_LED = -1

# Utilitários

def log_registro_removido(tam_registro: int, offset_registro: int):     # Imprime informações sobre o registro removido
    print(f'Registro removido! ({tam_registro} bytes)')
    print(f'Local: offset = {offset_registro} ({hex(offset_registro)})\n')

def log_insercao(id_registro: int, tam_registro: int, offset: int = 0, fragmentacao: int = 0):  # Registra no console a inserção de um registro
    print(f'Inserção do registro de chave "{id_registro}" ({tam_registro} bytes)')
    if fragmentacao == 0:       # Se não houve fragmentação, imprime apenas o offset
        print('Local: Fim do arquivo')
    else:              # Se houve fragmentação, imprime o espaço reutilizado e o offset
        print(f'Espaço reutilizado: {fragmentacao} bytes')
        print(f'Local: offset = {offset} bytes ({hex(offset)})')
    print('')

def log_busca(registro: str):       # Registra no console a busca de um registro
    id_registro = registro.split('|')[0]        # Extrai a chave do registro
    print(f'Busca pelo registro de chave "{id_registro}"')
    print(f'{registro} ({len(registro)} bytes)\n')

# LED

def ler_cabecalho_led(arq):     # Lê o cabeçalho do LED, que contém o offset do primeiro elemento
    arq.seek(0)
    return int.from_bytes(arq.read(4), byteorder='big', signed=True)

def escrever_cabecalho_led(arq, offset):        # Escreve o offset do primeiro elemento no cabeçalho do LED
    arq.seek(0)
    arq.write(offset.to_bytes(4, byteorder='big', signed=True))

def adicionar_novo_elemento_led(arq, offset_anterior, aponta_para):   # Adiciona um novo elemento na LED, apontando para o próximo elemento
    arq.seek(offset_anterior + 3)
    arq.write(aponta_para.to_bytes(4, byteorder='big', signed=True))

def remontar_led(led, arq, tam_reg, offset_novo):       # Remonta a LED após a remoção de um registro, inserindo o novo registro na posição correta
    offset_anterior = -1
    prox = led
    while prox != -1:       # Percorre a LED até encontrar o local adequado para inserir o novo registro
        arq.seek(prox)
        tam_atual = int.from_bytes(arq.read(2), 'big')      # Lê o tamanho do registro atual
        arq.read(1)     # Lê o byte de remoção (não utilizado aqui)
        prox_next = int.from_bytes(arq.read(4), 'big', signed=True)     # Lê o próximo elemento da LED

        if tam_reg <= tam_atual:    # Se o tamanho do novo registro é menor ou igual ao tamanho do registro atual
            if offset_anterior == -1:
                escrever_cabecalho_led(arq, offset_novo)    # Se for o primeiro elemento, atualiza o cabeçalho do LED
            else:
                adicionar_novo_elemento_led(arq, offset_anterior, offset_novo)   # Caso contrário, atualiza o elemento anterior para apontar para o novo registro

            adicionar_novo_elemento_led(arq, offset_novo, prox)   # O novo registro aponta para o próximo elemento da LED
            log_registro_removido(tam_reg, offset_novo)     # Registra a remoção do registro
            return

        offset_anterior = prox      # Atualiza o offset do elemento anterior
        prox = prox_next        # Avança para o próximo elemento da LED

    if offset_anterior != -1:
        adicionar_novo_elemento_led(arq, offset_anterior, offset_novo)      # Se não encontrou um local adequado, adiciona o novo registro ao final da LED
        adicionar_novo_elemento_led(arq, offset_novo, -1)           # O novo registro aponta para -1, indicando o fim da LED
        log_registro_removido(tam_reg, offset_novo)     # Registra a remoção do registro

def percorrer_led(cabeca, arq):     # Percorre a LED e imprime os elementos
    prox = cabeca   
    print('LED -> ', end='')    
    while prox != -1:       # Enquanto houver elementos na LED
        arq.seek(prox)
        tam = int.from_bytes(arq.read(2), 'big')        # Lê o tamanho do registro
        arq.read(1)
        prox_next = int.from_bytes(arq.read(4), 'big', signed=True)     # Lê o próximo elemento da LED
        print(f'[{prox}({tam}) -> {prox_next}] -> ', end='')        # Imprime o elemento atual
        prox = prox_next    
    print('FIM')

# Arquivo

def busca(chave, imprimir=True):        # Busca um registro pelo identificador (chave) no arquivo
    try:
        with open('filmes.dat', 'rb') as arq:       # Abre o arquivo em modo leitura binária
            arq.seek(4)             # Pula o cabeçalho do arquivo
            while True:             # Lê os registros até encontrar o registro com a chave especificada
                offset = arq.tell()         # Obtém o offset atual do arquivo
                tam_bytes = arq.read(2)     # Lê os 2 bytes que indicam o tamanho do registro
                if not tam_bytes or len(tam_bytes) < 2:     # Se não houver mais registros, sai do loop
                    break
                tam = int.from_bytes(tam_bytes, 'big')      # Converte os bytes lidos para um inteiro que representa o tamanho do registro
                data = arq.read(tam)                # Lê o registro do arquivo
                if data[:1] == REMOVIDO_FLAG:       # Se o registro foi removido, pula para o próximo
                    continue
                registro = data.decode('utf-8', 'replace')  # Decodifica o registro lido do arquivo
                if registro.split('|')[0] == chave:         # Se a chave do registro corresponde à chave procurada
                    if imprimir:            # Se a flag de impressão for verdadeira, imprime o registro encontrado  
                        log_busca(registro) 
                    return offset           # Retorna o offset do registro encontrado
        if imprimir:
            print(f'Jogo com identificador {chave} não encontrado.\n')      # Se não encontrar o registro, imprime mensagem de erro
        return -1       
    except OSError as e:
        print(f'Erro ao abrir "filmes.dat": {e}')       
        return -1 

def imprimir_led():     # Imprime o conteúdo da LED
    try:
        with open('filmes.dat', 'rb') as arq:       # Abre o arquivo em modo leitura binária
            cabeca = ler_cabecalho_led(arq)         # Lê o cabeçalho da LED
            if cabeca == -1:                        # Se a LED estiver vazia, imprime mensagem e sai
                print('LED está vazia.')
                return
            percorrer_led(cabeca, arq)              # Percorre a LED e imprime os elementos
    except OSError as e:
        print(f'Erro ao abrir o arquivo: {e}')

def inserir_em_espaco_led(registro, tam_disp, offsets, arq):        # Insere um registro em um espaço disponível na LED
    reg_bytes = registro.encode('utf-8')            # Converte o registro para bytes
    tam_reg = len(reg_bytes)        
    fragmentacao = tam_disp - tam_reg               # Calcula a fragmentação, ou seja, o espaço livre restante após a inserção
    if fragmentacao:
        reg_bytes = reg_bytes.ljust(tam_disp, b'\0')    # Preenche o registro com zeros até o tamanho do espaço disponível

    offset_ant, offset_disp = offsets       # Obtém os offsets do elemento anterior e do espaço disponível
    arq.seek(offset_disp + 3)               # Move o cursor para o espaço disponível na LED
    prox = int.from_bytes(arq.read(4), 'big', signed=True)      # Lê o próximo elemento da LED

    arq.seek(offset_disp)                   # Move o cursor para o início do espaço disponível
    arq.write(tam_disp.to_bytes(2, 'big'))  # Escreve o tamanho do registro no início do espaço disponível
    arq.write(reg_bytes)                    # Escreve o registro no espaço disponível

    if offset_ant == 0:                     # Se o elemento anterior for o cabeçalho da LED, atualiza o cabeçalho
        escrever_cabecalho_led(arq, prox)       
    else:                                    # Caso contrário, atualiza o elemento anterior para apontar para o novo registro
        arq.seek(offset_ant + 3)
        arq.write(prox.to_bytes(4, 'big', signed=True))     # Atualiza o próximo elemento do elemento anterior

    log_insercao(registro.split('|')[0], tam_reg, offset_disp, fragmentacao)        # Registra a inserção do registro

def procurar_espaco_disponivel_led(cabeca, tam_reg, arq):       # Procura um espaço disponível na LED para inserir um novo registro
    offset_ant = 0      # Inicializa o offset do elemento anterior como 0
    prox = cabeca       # Inicializa o próximo elemento como o cabeçalho da LED
    while prox != -1:   # Enquanto houver elementos na LED
        arq.seek(prox)
        tam = int.from_bytes(arq.read(2), 'big')        # Lê o tamanho do registro
        arq.read(1)
        prox_next = int.from_bytes(arq.read(4), 'big', signed=True)         # Lê o próximo elemento da LED
        if tam >= tam_reg:
            return True, tam, (offset_ant, prox)        # Se o tamanho do registro for maior ou igual ao tamanho do espaço disponível, retorna True e os offsets
        offset_ant = prox       # Atualiza o offset do elemento anterior
        prox = prox_next        # Avança para o próximo elemento da LED
    return False, -1, (offset_ant, prox)        # Se não encontrar espaço, retorna False e os offsets do último elemento

def insere(registro):           # Insere um novo registro no arquivo
    try:
        with open('filmes.dat', 'r+b') as arq:          # Abre o arquivo em modo leitura e escrita binária
            cabeca = ler_cabecalho_led(arq)             # Lê o cabeçalho da LED
            tam_reg = len(registro.encode('utf-8'))     # Calcula o tamanho do registro
            encontrado, tam_disp, offsets = procurar_espaco_disponivel_led(cabeca, tam_reg, arq)        # Procura um espaço disponível na LED para inserir o registro
            if encontrado:
                inserir_em_espaco_led(registro, tam_disp, offsets, arq)     # Se encontrar um espaço disponível, insere o registro nesse espaço
            else:
                arq.seek(0, io.SEEK_END)        # Se não encontrar espaço, insere o registro no final do arquivo
                arq.write(tam_reg.to_bytes(2, 'big'))       # Escreve o tamanho do registro no início do espaço
                arq.write(registro.encode('utf-8'))         # Escreve o registro no espaço
                log_insercao(registro.split('|')[0], tam_reg)          # Registra a inserção do registro
    except OSError as e:
        print(f'Erro ao abrir "filmes.dat": {e}')

def remove(chave):          # Remove um registro do arquivo pelo identificador (chave)
    try:
        offset = busca(chave, imprimir=False)               # Busca o registro pelo identificador
        print(f'Remoção do registro de chave "{chave}"')    
        if offset == -1:                                    # Se o registro não for encontrado, imprime mensagem de erro e sai
            print('Erro: registro não encontrado!\n')
            return
        with open('filmes.dat', 'r+b') as arq:              # Abre o arquivo em modo leitura e escrita binária
            arq.seek(offset)                                # Move o cursor para o offset do registro encontrado
            tam_bytes = arq.read(2)                         # Lê os 2 bytes que indicam o tamanho do registro
            tam = int.from_bytes(tam_bytes, 'big')          # Converte os bytes lidos para um inteiro que representa o tamanho do registro

            arq.seek(offset + 2)                # Move o cursor para o byte que indica se o registro foi removido
            arq.write(REMOVIDO_FLAG)            # Marca o registro como removido escrevendo o byte de remoção
            arq.write(b'\0' * (tam - 1))        # Preenche o restante do registro com zeros para manter o tamanho do registro

            cabeca = ler_cabecalho_led(arq)     # Lê o cabeçalho da LED
            escrever_cabecalho_led(arq, offset)     # Atualiza o cabeçalho da LED para apontar para o registro removido
            arq.seek(offset + 3)
            arq.write(cabeca.to_bytes(4, 'big', signed=True))       # O registro removido aponta para o próximo elemento da LED
            log_registro_removido(tam, offset)                      # Registra a remoção do registro
    except OSError as e:
        print(f'Erro ao abrir "filmes.dat": {e}')

def compactar():        # Compacta o arquivo removendo os registros marcados como removidos
    try:
        with open('filmes.dat', 'rb') as origem, open('filmes_compactado.dat', 'wb') as destino:
            destino.write(int(0).to_bytes(4, 'big', signed=True))   # Cabeçalho da LED zerado
            origem.seek(4)                                          # Pula o cabeçalho do arquivo original

            while True:
                tam_bytes = origem.read(2)          # Lê os 2 bytes que indicam o tamanho do registro
                if not tam_bytes:                   # Se não houver mais registros, sai do loop
                    break
                tam = int.from_bytes(tam_bytes, 'big')      # Converte os bytes lidos para um inteiro que representa o tamanho do registro
                conteudo = origem.read(tam)                 # Lê o registro do arquivo original
                if conteudo[:1] != REMOVIDO_FLAG:           # Ignora registros removidos
                    destino.write(tam.to_bytes(2, 'big'))   # Escreve o tamanho do registro no arquivo compactado
                    destino.write(conteudo)                 # Escreve o registro no arquivo compactado

            print('Compactação concluída: filmes_compactado.dat')
    except OSError as e:
        print(f'Erro na compactação: {e}')

def arquivo(nomeArq):          # Lê um arquivo de operações e executa as operações de busca, remoção e inserção
    try:
        with open(nomeArq, 'r') as arq:
            for linha in arq:
                linha = linha.strip()
                if not linha: continue
                oper = linha[0]
                dados = linha[2:]
                if oper == 'b':               # Busca um registro
                    busca(dados)
                elif oper == 'r':             # Remove um registro
                    remove(dados)
                elif oper == 'i':             # Insere um registro
                    insere(dados)
    except OSError as e:
        print(f'Erro ao abrir "{nomeArq}": {e}')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '-e':          # Executa operações a partir de um arquivo
        arquivo(sys.argv[2])
    elif len(sys.argv) == 2 and sys.argv[1] == '-p':        # Imprime o conteúdo da LED
        imprimir_led()
    elif len(sys.argv) == 2 and sys.argv[1] == '-c':        # Compacta o arquivo removendo registros marcados como removidos
        compactar()
    else:
        print("Uso: python programa.py -e operacoes.txt")
        print("Ou: python programa.py -p")
        print("Ou: python programa.py -c")