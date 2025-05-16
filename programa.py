import argparse
import os

# Robson Oliveira de Souza

TAM_CABECALHO = 4
TAM_TAM_REGISTRO = 2
ARQUIVO = 'filmes.dat'

def le_cabeca_led(arquivo):
    arquivo.seek(0)
    cabeca_bytes = arquivo.read(4)
    if len(cabeca_bytes) < 4:
        return -1 
    return int.from_bytes(cabeca_bytes, byteorder='big', signed=True)

def monta_led(arquivo):
    led = []
    pos = le_cabeca_led(arquivo)
    while pos != -1 and pos != 0:
        arquivo.seek(pos)
        tam_bytes = arquivo.read(2)
        if len(tam_bytes) < 2:
            break
        tam = int.from_bytes(tam_bytes, byteorder='big')
        prox_bytes = arquivo.read(4)
        if len(prox_bytes) < 4:
            break
        prox = int.from_bytes(prox_bytes, byteorder='big', signed=True)
        led.append({'offset': pos, 'tamanho': tam, 'proximo': prox})
        pos = prox
    return led

def remove_no_led(arquivo, offset_remocao):
    cabeca = le_cabeca_led(arquivo)
    if cabeca == offset_remocao:
        arquivo.seek(offset_remocao + TAM_TAM_REGISTRO)
        prox = int.from_bytes(arquivo.read(4), 'big', signed=True)
        arquivo.seek(0)
        arquivo.write(prox.to_bytes(4, 'big', signed=True))
    else:
        pos = cabeca
        while pos != -1:
            arquivo.seek(pos + TAM_TAM_REGISTRO)
            prox = int.from_bytes(arquivo.read(4), 'big', signed=True)
            if prox == offset_remocao:
                arquivo.seek(offset_remocao + TAM_TAM_REGISTRO)
                novo_prox = int.from_bytes(arquivo.read(4), 'big', signed=True)
                arquivo.seek(pos + TAM_TAM_REGISTRO)
                arquivo.write(novo_prox.to_bytes(4, 'big', signed=True))
                break
            pos = prox

def adiciona_no_led(arquivo, offset_removido, tamanho):
    cabeca = le_cabeca_led(arquivo)
    arquivo.seek(offset_removido)
    arquivo.write(tamanho.to_bytes(2, 'big'))
    arquivo.write(cabeca.to_bytes(4, 'big', signed=True))
    arquivo.seek(0)
    arquivo.write(offset_removido.to_bytes(4, 'big', signed=True))


def busca_best_fit(led, tamanho_necessario):
    melhor = None
    for espaco in led:
        if espaco['tamanho'] >= tamanho_necessario:
            if melhor is None or espaco['tamanho'] < melhor['tamanho']:
                melhor = espaco
    return melhor

def busca(id_busca):
    id_busca = str(id_busca)
    print(f"\nBusca pelo registro de chave \"{id_busca}\"")

    with open(ARQUIVO, 'rb') as arquivo:
        arquivo.seek(TAM_CABECALHO)
        while True:
            tam_bytes = arquivo.read(TAM_TAM_REGISTRO)
            if not tam_bytes or len(tam_bytes) < TAM_TAM_REGISTRO:
                break

            tam = int.from_bytes(tam_bytes, 'big')
            registro = arquivo.read(tam)

            if registro.startswith(b'*|'):
                continue

            try:
                texto = registro.decode('utf-8')
                campos = texto.split('|')
                if campos[0] == id_busca:
                    print(texto)
                    return
            except:
                continue

        print("Erro: registro não encontrado!")

def atualiza_led(arquivo, offset_antigo, offset_novo):
    cabeca = le_cabeca_led(arquivo)

    if cabeca == offset_antigo:
        arquivo.seek(offset_novo + TAM_TAM_REGISTRO)
        prox = int.from_bytes(arquivo.read(4), 'big', signed=True)
        arquivo.seek(0)
        arquivo.write(offset_novo.to_bytes(4, 'big', signed=True))
    else:
        pos = cabeca
        while pos != -1:
            arquivo.seek(pos + TAM_TAM_REGISTRO)
            prox = int.from_bytes(arquivo.read(4), 'big', signed=True)
            if prox == offset_antigo:
                arquivo.seek(pos + TAM_TAM_REGISTRO)
                arquivo.write(offset_novo.to_bytes(4, 'big', signed=True))
                break
            pos = prox


def insere_no_espaco(arquivo, espaco, registro_bytes):
    tam_reg = len(registro_bytes)
    sobra = espaco['tamanho'] - tam_reg

    arquivo.seek(espaco['offset'])
    arquivo.write(tam_reg.to_bytes(2, byteorder='big'))
    arquivo.write(registro_bytes)

    if sobra > 6:
        novo_offset = arquivo.tell()
        novo_tam = sobra
        arquivo.write(novo_tam.to_bytes(2, byteorder='big'))
        arquivo.write(espaco['proximo'].to_bytes(4, byteorder='big', signed=True))

        atualiza_led(arquivo, espaco['offset'], novo_offset)
    else:
        remove_no_led(arquivo, espaco['offset'])

def insere(registro_str):
    campos = registro_str.split('|')
    id_filme = campos[0].strip()

    registro_bytes = registro_str.encode('utf-8')
    tam_reg = len(registro_bytes) + 2

    with open(ARQUIVO, 'r+b') as arquivo:
        led = monta_led(arquivo)
        melhor_espaco = busca_best_fit(led, tam_reg)

        if melhor_espaco:
            insere_no_espaco(arquivo, melhor_espaco, registro_bytes)
            print(f"Registro {id_filme} inserido, reutilizado espaço offset {melhor_espaco['offset']}")
        else:
            arquivo.seek(0, os.SEEK_END)
            arquivo.write(tam_reg.to_bytes(2, byteorder='big'))
            arquivo.write(registro_bytes)
            print(f"Registro {id_filme} inserido no fim do arquivo")

def remove(id_remover):
    id_remover = str(id_remover)
    print(f'\nRemoção do registro de chave \"{id_remover}\"')

    with open(ARQUIVO, 'r+b') as arquivo:
        led = monta_led(arquivo)
        offsets_led = {esp['offset'] for esp in led}

        arquivo.seek(0, os.SEEK_END)
        tamanho_total = arquivo.tell()

        pos = TAM_CABECALHO
        while pos < tamanho_total:
            if pos in offsets_led:

                arquivo.seek(pos)
                tam_led = int.from_bytes(arquivo.read(2), 'big')
                pos += TAM_TAM_REGISTRO + tam_led
                continue

            arquivo.seek(pos)
            tam_bytes = arquivo.read(TAM_TAM_REGISTRO)
            if len(tam_bytes) < TAM_TAM_REGISTRO:
                break

            tam = int.from_bytes(tam_bytes, 'big')
            pos_inicio_registro = pos + TAM_TAM_REGISTRO
            arquivo.seek(pos_inicio_registro)
            registro_bytes = arquivo.read(tam)

            if not registro_bytes or registro_bytes.startswith(b'*|'):
                pos = pos + TAM_TAM_REGISTRO + tam
                continue

            try:
                registro = registro_bytes.decode('utf-8').strip()
                campos = registro.split('|')
                id_lido = campos[0].strip()

                if id_lido == id_remover:
                    arquivo.seek(pos_inicio_registro)
                    arquivo.write('*|'.encode('utf-8'))
                    print(f"Registro removido! ({tam} bytes)")
                    print(f"Local: offset = {pos} bytes ({hex(pos)})")
                    adiciona_no_led(arquivo, pos, TAM_TAM_REGISTRO + tam)
                    return
            except UnicodeDecodeError as e:
                print(f"[Erro ao decodificar registro em {pos}: {e}]")

            pos = pos + TAM_TAM_REGISTRO + tam

        print("Erro: registro não encontrado!")

def imprime_led():
    with open(ARQUIVO, 'rb') as arquivo:
        led = monta_led(arquivo)
        if not led:
            print("LED -> [FIM]")
            return
        print("LED ->", end=" ")
        for espaco in led:
            print(f"[offset: {espaco['offset']}, tam: {espaco['tamanho']}] ->", end=" ")
        print("[FIM]")
        print(f"Total: {len(led)} espaços disponíveis")

def compacta_arquivo():
    if not os.path.exists(ARQUIVO):
        print("Erro: arquivo não encontrado.")
        return

    novo_nome = 'filmes_temp.dat'

    with open(ARQUIVO, 'rb') as antigo, open(novo_nome, 'wb') as novo:
        novo.write((0).to_bytes(4, 'big', signed=True))

        antigo.seek(TAM_CABECALHO)
        while True:
            tam_bytes = antigo.read(TAM_TAM_REGISTRO)
            if len(tam_bytes) < TAM_TAM_REGISTRO:
                break
            tam = int.from_bytes(tam_bytes, 'big')
            registro = antigo.read(tam)
            if not registro or registro.startswith(b'*|'):
                continue
            novo.write(len(registro).to_bytes(2, 'big'))
            novo.write(registro)

    os.replace(novo_nome, ARQUIVO)
    print("Arquivo compactado com sucesso.")

def main():
    parser = argparse.ArgumentParser(description='Gerenciador de Filmes com LED - Best-Fit')
    parser.add_argument('-e', dest='arquivo_operacoes', help='Arquivo de operações')
    parser.add_argument('-p', action='store_true', help='Imprime a LED')
    parser.add_argument('-c', action='store_true', help='Compacta o arquivo')

    args = parser.parse_args()

    if args.p:
        imprime_led()
    elif args.c:
        compacta_arquivo()
    elif args.arquivo_operacoes:
        try:
            with open(args.arquivo_operacoes, 'r') as file:
                operacoes = file.readlines()
                for linha in operacoes:
                    op = linha[0].lower()
                    conteudo = linha[2:].strip()
                    if op == 'i':
                        insere(conteudo)
                    elif op == 'r':
                        remove(conteudo)
                    elif op == 'b':
                        busca(conteudo)
                    else:
                        print(f"Operação desconhecida: {linha}")
        except FileNotFoundError:
            print(f"Arquivo {args.arquivo_operacoes} não encontrado.")
    else:
        print("Nenhum argumento válido fornecido. Use:\n"
              "  -e arquivo_operacoes\n"
              "  -p (para imprimir a LED)\n"
              "  -c (para compactar o arquivo)")

if __name__ == '__main__':
    main()