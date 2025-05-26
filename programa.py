import sys
import io

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

def reinserirSobraLED(arq, sobra, offsetSobra):
    arq.seek(0)
    ledCabecalho = arq.read(4)
    led = int.from_bytes(ledCabecalho, byteorder='big', signed=True)
    offsetAnterior = -1
    offsetAtual = led
    inserido = False
    while offsetAtual != -1 and not inserido:
        arq.seek(offsetAtual)
        espacoAtual = int.from_bytes(arq.read(2), byteorder='big')
        arq.read(1)
        proxOffset = int.from_bytes(arq.read(4), byteorder='big', signed=True)
        if sobra < espacoAtual:
            if offsetAnterior == -1:
                arq.seek(0)
                arq.write(offsetSobra.to_bytes(4, byteorder='big', signed=True))
            else:
                arq.seek(offsetAnterior + 3)
                arq.write(offsetSobra.to_bytes(4, byteorder='big', signed=True))
            arq.seek(offsetSobra)
            arq.write(sobra.to_bytes(2, byteorder='big'))
            arq.write(b"*")
            arq.write(offsetAtual.to_bytes(4, byteorder='big', signed=True))
            inserido = True
        else:
            offsetAnterior = offsetAtual
            offsetAtual = proxOffset
    if not inserido:
        if offsetAnterior == -1:
            arq.seek(0)
            arq.write(offsetSobra.to_bytes(4, byteorder='big', signed=True))
        else:
            arq.seek(offsetAnterior + 3)
            arq.write(offsetSobra.to_bytes(4, byteorder='big', signed=True))
        arq.seek(offsetSobra)
        arq.write(sobra.to_bytes(2, byteorder='big'))
        arq.write(b"*")
        arq.write((-1).to_bytes(4, byteorder='big', signed=True))

def insere(registro):
    try:
        chave = registro.split('|')[0]
        with open("filmes.dat", 'r+b') as arq:
            arq.seek(0)
            ledCabecalho = arq.read(4)
            led = int.from_bytes(ledCabecalho, byteorder='big', signed=True)
            print(f'Inserção do registro de chave "{chave}" ({len(registro)} bytes)')
            tamRegistro = len(registro)
            encontrado = False
            offsetAnterior = -1
            offsetAtual = led
            offsetInsercao = None
            espaco = None
            while offsetAtual != -1 and not encontrado:
                arq.seek(offsetAtual)
                espaco = int.from_bytes(arq.read(2), byteorder='big')
                arq.read(1)
                proxOffset = int.from_bytes(arq.read(4), byteorder='big', signed=True)
                if espaco >= tamRegistro:
                    encontrado = True
                    sobra = espaco - tamRegistro - 2
                    if offsetAnterior == -1:
                        arq.seek(0)
                        arq.write(proxOffset.to_bytes(4, byteorder='big', signed=True))
                    else:
                        arq.seek(offsetAnterior + 3)
                        arq.write(proxOffset.to_bytes(4, byteorder='big', signed=True))
                    arq.seek(offsetAtual)
                    arq.write(tamRegistro.to_bytes(2, byteorder='big'))
                    arq.write(registro.encode('utf-8'))
                    offsetInsercao = offsetAtual + tamRegistro + 2
                else:
                    offsetAnterior = offsetAtual
                    offsetAtual = proxOffset
            if encontrado:
                if sobra > 10:
                    print(f"Tamanho do espaço reutilizado: {espaco} bytes (Sobra de {sobra} bytes)")
                    print(f"Local: offset = {offsetAtual} ({ledCabecalho})\n")
                    reinserirSobraLED(arq, sobra, offsetInsercao)
                else:
                    print(f"Tamanho do espaço reutilizado: {espaco} bytes")
                    print(f"Local: offset = {offsetAtual} ({ledCabecalho})\n")
            else:
                arq.seek(0, io.SEEK_END)
                posicao = arq.tell()
                arq.write(tamRegistro.to_bytes(2, byteorder='big'))
                arq.write(registro.encode('utf-8'))
                print(f'Tamanho do espaço utilizado: {tamRegistro} bytes')
                print(f'Local: fim do arquivo (offset = {posicao})\n')
    except OSError as e:
        print(f"Erro ao abrir 'filmes.dat': {e}")

def remove(chave):
    try:
        offset = busca(chave, imprimir=False)
        if offset == -1:
            print(f'Remoção do registro de chave "{chave}"')
            print('Erro: registro não encontrado!\n')
            return
        with open("filmes.dat", 'r+b') as arq:
            arq.seek(0)
            ledCabecalho = arq.read(4)
            led = int.from_bytes(ledCabecalho, byteorder='big', signed=True)
            arq.seek(offset)
            tamBytes = arq.read(2)
            if tamBytes:
                tam = int.from_bytes(tamBytes, byteorder='big')
                arq.read(tam)
                print(f'Remoção do registro de chave "{chave}"')
                arq.seek(offset + 2)
                arq.write(b'*')
                novoEspacoTam = tam
                novoEspacoOffset = offset
                if led == -1:
                    arq.seek(0)
                    arq.write(novoEspacoOffset.to_bytes(4, byteorder='big', signed=True))
                    arq.seek(novoEspacoOffset + 3)
                    arq.write((-1).to_bytes(4, byteorder='big', signed=True))
                else:
                    antOffset = -1
                    atualOffset = led
                    while atualOffset != -1:
                        arq.seek(atualOffset)
                        atualEspacoTam = int.from_bytes(arq.read(2), byteorder='big')
                        arq.read(1)
                        proxOffset = int.from_bytes(arq.read(4), byteorder='big', signed=True)
                        if novoEspacoTam < atualEspacoTam:  # BEST-FIT!!!
                            break
                        antOffset = atualOffset
                        atualOffset = proxOffset
                    if antOffset == -1:
                        arq.seek(0)
                        arq.write(novoEspacoOffset.to_bytes(4, byteorder='big', signed=True))
                    else:
                        arq.seek(antOffset + 3)
                        arq.write(novoEspacoOffset.to_bytes(4, byteorder='big', signed=True))
                    arq.seek(novoEspacoOffset + 3)
                    arq.write(atualOffset.to_bytes(4, byteorder='big', signed=True))
                print(f'Registro removido! ({tam} bytes)')
                print(f'Local: offset = {offset}\n')
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
