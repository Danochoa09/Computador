import utils
from utils import NumberConversion as NC
from utils import Math

import unittest


class TestBinaryConversion(unittest.TestCase):

    def test_positive_values(self):
        self.assertEqual(
            NC.int2bitarray(5, bits=4).to01(), "0101"
        )
        self.assertEqual(
            NC.int2bitarray(1, bits=4).to01(), "0001"
        )
        self.assertEqual(
            NC.int2bitarray(0, bits=4).to01(), "0000"
        )

    def test_negative_values(self):
        self.assertEqual(
            NC.int2bitarray(-1, bits=4).to01(), "1111"
        )
        self.assertEqual(
            NC.int2bitarray(-8, bits=4).to01(), "1000"
        )
        self.assertEqual(
            NC.int2bitarray(-5, bits=4).to01(), "1011"
        )

    def test_automatic_bit_length(self):
        # 5 in binary is '101', needs 4 bits with sign
        self.assertEqual(
            NC.int2bitarray(5).to01(), "0101"
        )
        # -1 needs 2 bits minimum (1 bit for sign and 1 bit for value)
        self.assertEqual(
            NC.int2bitarray(-1).to01(), "11"
        )

    def test_truncation(self):
        # 8 in 4 bits: no cabe, pero truncado da '1000'
        self.assertEqual(
            NC.int2bitarray(8, bits=4, truncate=True).to01(), "1000"
        )
        # -9 en 4 bits, truncado da '0111' (valor real -7 por overflow)
        self.assertEqual(
            NC.int2bitarray(-9, bits=4, truncate=True).to01(), "0111"
        )

    def test_error_when_out_of_range(self):
        with self.assertRaises(ValueError):
            NC.int2bitarray(9, bits=4)  # 9 no cabe en 4 bits C2

        with self.assertRaises(ValueError):
            NC.int2bitarray(-9, bits=4)  # tampoco cabe sin truncar

    def test_binary_list2str_basic(self):
        self.assertEqual(NC.binary_list2str([1, 0, 1, 1]), "1011")
        self.assertEqual(NC.binary_list2str([0, 0, 0]), "000")
        self.assertEqual(NC.binary_list2str([]), "")

    def test_str2binary_list_basic(self):
        self.assertEqual(NC.str2binary_list("1011"), [1, 0, 1, 1])
        self.assertEqual(NC.str2binary_list("000"), [0, 0, 0])
        self.assertEqual(NC.str2binary_list(""), [])

    def test_round_trip(self):
        for s in ["0", "1", "10", "11001", "000111000"]:
            binary_list = NC.str2binary_list(s)
            reconstructed = NC.binary_list2str(binary_list)
            self.assertEqual(reconstructed, s)

    def test_str2binary_list_invalid(self):
        with self.assertRaises(ValueError):
            NC.str2binary_list("10201")

        with self.assertRaises(ValueError):
            NC.str2binary_list("abc01")

        with self.assertRaises(ValueError):
            NC.str2binary_list("10 01")  # espacio no permitido

    def test_entero2binary_list_positive(self):
        self.assertEqual(NC.entero2binary_list(5, fix_bits=8), [0, 0, 0, 0, 0, 1, 0, 1])
        self.assertEqual(NC.entero2binary_list(0, fix_bits=8), [0] * 8)
        self.assertEqual(NC.entero2binary_list(127, fix_bits=8), [0, 1, 1, 1, 1, 1, 1, 1])

    def test_entero2binary_list_negative(self):
        self.assertEqual(NC.entero2binary_list(-1, fix_bits=8), [1, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual(NC.entero2binary_list(-128, fix_bits=8), [1, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(NC.entero2binary_list(-5, fix_bits=8), [1, 1, 1, 1, 1, 0, 1, 1])

    def test_binary_list2entero_positive(self):
        self.assertEqual(NC.binary_list2entero([0, 0, 0, 0, 0, 1, 0, 1]), 5)
        self.assertEqual(NC.binary_list2entero([0] * 8), 0)
        self.assertEqual(NC.binary_list2entero([0, 1, 1, 1, 1, 1, 1, 1]), 127)

    def test_binary_list2entero_negative(self):
        self.assertEqual(NC.binary_list2entero([1, 1, 1, 1, 1, 1, 1, 1]), -1)
        self.assertEqual(NC.binary_list2entero([1, 0, 0, 0, 0, 0, 0, 0]), -128)
        self.assertEqual(NC.binary_list2entero([1, 1, 1, 1, 1, 0, 1, 1]), -5)

    def test_round_trip(self):
        for n in range(-128, 128):
            bits = NC.entero2binary_list(n, fix_bits=8)
            recovered = NC.binary_list2entero(bits)
            self.assertEqual(n, recovered, f"Falla en round-trip con n={n}")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            NC.binary_list2entero([])

        with self.assertRaises(ValueError):
            NC.binary_list2entero([0, 2, 1])

        with self.assertRaises(ValueError):
            NC.entero2binary_list("no es un entero", fix_bits=8)

        with self.assertRaises(ValueError):
            NC.entero2binary_list(200, fix_bits=8)

        with self.assertRaises(ValueError):
            NC.entero2binary_list(5, fix_bits=0)

    def test_natural2binary_list_basic(self):
        self.assertEqual(NC.natural2binary_list(0, fix_bits=8), [0] * 8)
        self.assertEqual(NC.natural2binary_list(5, fix_bits=4), [0, 1, 0, 1])
        self.assertEqual(NC.natural2binary_list(15, fix_bits=4), [1, 1, 1, 1])

    def test_binary_list2natural_basic(self):
        self.assertEqual(NC.binary_list2natural([0, 0, 0, 0]), 0)
        self.assertEqual(NC.binary_list2natural([1, 0, 1]), 5)
        self.assertEqual(NC.binary_list2natural([1, 1, 1, 1]), 15)

    def test_round_trip_fixed_bits(self):
        for n in range(0, 128):
            bits = max(n.bit_length(), 1)
            bin_list = NC.natural2binary_list(n, fix_bits=bits)
            reconstructed = NC.binary_list2natural(bin_list)
            self.assertEqual(n, reconstructed, f"Falla en round-trip con n={n}, bin={bin_list}")

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            NC.natural2binary_list(-1, fix_bits=8)
        with self.assertRaises(ValueError):
            NC.natural2binary_list(-100)

    def test_variable_bits(self):
        # Sin fix_bits
        self.assertEqual(NC.natural2binary_list(5, fix_bits=None), [1, 0, 1])
        self.assertEqual(NC.natural2binary_list(0, fix_bits=None), [0])


class TestHuffmanSet(unittest.TestCase):
    def test_huffman_set(self):
        # Entrada de prueba
        input_data = [(64, 3), (54, 9), (59, 6), (35, 24), (27, 10), (40, 10)]

        # Generar códigos
        huffman_dict = Math.huffman_set(input_data)

        # Verificar total de códigos generados
        total_expected = sum(q for _, q in input_data)
        total_generated = sum(len(lst) for lst in huffman_dict.values())
        self.assertEqual(total_generated, total_expected, "Cantidad total incorrecta de códigos")

        # Verificar longitudes y estructura
        for length, count in input_data:
            self.assertIn(length, huffman_dict, f"No se encontraron códigos de longitud {length}")
            self.assertEqual(len(huffman_dict[length]), count, f"Cantidad incorrecta de códigos de longitud {length}")

            # Verificar que cada código tenga la longitud correcta
            for code in huffman_dict[length]:
                self.assertEqual(len(code), length, f"Código {code} no tiene longitud {length}")

        # Verificar que el conjunto total sea prefix-free
        all_codes_str = [''.join(map(str, code)) for group in huffman_dict.values() for code in group]
        all_codes_str.sort()
        for i in range(len(all_codes_str) - 1):
            c1 = all_codes_str[i]
            c2 = all_codes_str[i + 1]
            self.assertFalse(c2.startswith(c1), f"Ambigüedad detectada: {c1} es prefijo de {c2}")


if __name__ == '__main__':
    unittest.main()
