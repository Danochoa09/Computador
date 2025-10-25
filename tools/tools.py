import constants

from utils import Math, FileManager, NumberConversion

def get_huffman_for_instructions():
    dict_isa = FileManager.JSON.JSON2dict(constants.ISA_PATH)

    huff_list = []
    for length, ISA_list in dict_isa.items():
        huff_list.append((int(length), len(ISA_list)))

    huffman_dict:dict[int, list[list[int]]] = Math.huffman_set(huff_list)

    for key, value in huffman_dict.items():
        huffman_dict[key] = []
        for code in value:
            huffman_dict[key].append(NumberConversion.binary_list2str(code))
    FileManager.JSON.dict2JSON(constants.OPCODES_PATH, huffman_dict)
