def senha_forte(senha):
    if not senha:
        return False

    maiusculo = minuscula = numero = caracterEspecial = False

    for s in senha:
        if s.isupper():
            maiusculo = True
        elif s.islower():
            minuscula = True
        elif s.isdigit():
            numero = True
        elif not s.isalnum():
            caracterEspecial = True

    if len(senha) >= 8 and maiusculo and minuscula and numero and caracterEspecial:
        return True
    else:
        return False