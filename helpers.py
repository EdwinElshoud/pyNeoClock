# Workaround for using enums
def enum(**enums: int):
    return type('Enum', (), enums)
