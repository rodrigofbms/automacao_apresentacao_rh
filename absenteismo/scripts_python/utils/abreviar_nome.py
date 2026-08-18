




def abreviar_nome(nome, max_chars=45):
    return nome if len(nome) <= max_chars else nome[:max_chars].rstrip() + '...'