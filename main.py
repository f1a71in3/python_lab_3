import re
from PIL import Image

# 1.1 Декодирование из синего канала по координатам
def decode_from_blue_channel(img_path: str, keys_path: str) -> str:
    """
    Декодирует текст, записанный в синий канал пикселей по координатам из файла.
    В случае любой ошибки возвращает пустую строку и печатает проблему.
    """
    try:
        img = Image.open(img_path).convert('RGB')
    except FileNotFoundError:
        print(f"Ошибка: файл изображения '{img_path}' не найден.")
        return ""
    except Exception as e:
        print(f"Ошибка при открытии изображения: {e}")
        return ""

    pixels = img.load()
    width, height = img.size

    # Чтение координат из keys1.txt
    coords = []
    try:
        with open(keys_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    coord = eval(line)
                    if isinstance(coord, tuple) and len(coord) == 2:
                        x, y = coord
                    else:
                        raise ValueError("Не кортеж из двух элементов")
                except Exception:
                    print(f"Предупреждение: строка {line_num} в '{keys_path}' не является парой координат: {line}")
                    continue

                # Проверка, что координаты внутри изображения
                if x >= width or y >= height:
                    print(
                        f"Предупреждение: координаты ({x},{y}) выходят за пределы изображения {width}x{height}, пропущены.")
                    continue
                coords.append((x, y))
    except FileNotFoundError:
        print(f"Ошибка: файл с ключами '{keys_path}' не найден.")
        return ""
    except Exception as e:
        print(f"Ошибка при чтении ключей: {e}")
        return ""

    if not coords:
        print("Нет корректных координат для декодирования.")
        return ""

    # Декодирование
    decoded_chars = []
    for x, y in coords:
        try:
            r, g, b = pixels[x, y]
            decoded_chars.append(chr(b))
        except Exception as e:
            print(f"Ошибка чтения пикселя ({x},{y}): {e}")
            continue

    return ''.join(decoded_chars)


# 1.2 Кодирование и декодирование через LSB красного канала
def text_to_bits(text: str):
    """Преобразует текст в список битов (с завершающим нулевым байтом)."""
    bits = []
    for ch in text:
        bits.extend([int(b) for b in format(ord(ch), '08b')])
    bits.extend([0] * 8)  # терминатор
    return bits


def bits_to_text(bits):
    """Преобразует список битов обратно в текст, останавливаясь на нулевом байте."""
    chars = []
    for i in range(0, len(bits), 8):
        if i + 8 > len(bits):
            break
        byte_bits = bits[i:i+8]
        char_code = int(''.join(str(b) for b in byte_bits), 2)
        if char_code == 0:
            break
        chars.append(chr(char_code))
    return ''.join(chars)


def encode_text_in_image(img_path: str, text: str, output_path: str):
    """
    Кодирует текст в LSB красного канала изображения.
    Выводит подробности изменения первых 8 бит (первый символ).
    При ошибке печатает сообщение и не сохраняет файл.
    """
    # Проверка входного текста
    if not text:
        print("Нет текста для кодирования.")
        return

    try:
        img = Image.open(img_path).convert('RGB')
    except FileNotFoundError:
        print(f"Ошибка: исходный файл '{img_path}' не найден.")
        return
    except Exception as e:
        print(f"Ошибка открытия изображения: {e}")
        return

    pixels = img.load()
    width, height = img.size
    total_pixels = width * height

    bits = text_to_bits(text)
    if len(bits) > total_pixels:
        print(f"Ошибка: нужно {len(bits)} бит, доступно только {total_pixels} пикселей. Сообщение слишком длинное.")
        return

    # Подготовка информации для вывода о первом символе
    first_char = text[0] if text else ''
    first_char_bits = [int(b) for b in format(ord(first_char), '08b')] if first_char else []
    encoded_info = []

    bit_index = 0
    modified_pixels = 0
    try:
        for y in range(height):
            for x in range(width):
                if bit_index >= len(bits):
                    break
                r, g, b = pixels[x, y]
                new_bit = bits[bit_index]
                new_r = (r & ~1) | new_bit
                pixels[x, y] = (new_r, g, b)

                if bit_index < 8:  # запоминаем для отчёта по первому символу
                    encoded_info.append({
                        'coord': (x, y),
                        'original_red': r,
                        'new_red': new_r,
                        'bit': new_bit
                    })
                bit_index += 1
                modified_pixels += 1
            if bit_index >= len(bits):
                break
    except Exception as e:
        print(f"Ошибка при изменении пикселей: {e}")
        return

    # Вывод отладочной информации
    if first_char_bits:
        print(f"Биты первого символа ('{first_char}') : {first_char_bits}")
    else:
        print("Первый символ отсутствует.")

    print("\nИзменения красного канала для битов первого символа:")
    for idx, info in enumerate(encoded_info):
        x, y = info['coord']
        orig = info['original_red']
        new = info['new_red']
        print(f"Пиксель ({x:3d},{y:3d}) : R исходный = {orig:3d} ({orig:08b}), "
              f"бит={info['bit']} → R новый = {new:3d} ({new:08b})")

    # Сохранение результата
    try:
        img.save(output_path)
        print(f"\nИзображение успешно сохранено как '{output_path}'. Изменено {modified_pixels} пикселей.")
    except Exception as e:
        print(f"Ошибка при сохранении изображения: {e}")


def decode_text_from_image(img_path: str) -> str:
    """Декодирует текст из LSB красного канала изображения. При ошибке возвращает пустую строку."""
    try:
        img = Image.open(img_path).convert('RGB')
    except FileNotFoundError:
        print(f"Ошибка: файл '{img_path}' не найден.")
        return ""
    except Exception as e:
        print(f"Ошибка открытия изображения: {e}")
        return ""

    pixels = img.load()
    width, height = img.size
    bits = []
    try:
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                bits.append(r & 1)
    except Exception as e:
        print(f"Ошибка при чтении пикселей: {e}")
        return ""

    return bits_to_text(bits)


# Основная программа
def main():
    # 1.1 Декодирование из изображения new1.png по ключам keys1.txt (синий канал)
    print("\nДекодирование скрытого текста (синий канал)")
    decoded_blue = decode_from_blue_channel('new1.png', 'keys1.txt')
    if decoded_blue:
        print(f"Декодированное сообщение:\n{decoded_blue}")
    else:
        print("Не удалось декодировать сообщение из синего канала.")

    # 1.2 Кодирование и декодирование через LSB красного канала
    print("\nКодирование/декодирование через красный канал (LSB)")
    source_img = 'new1.png'
    output_img = 'my_img.png'
    secret_message = "Simple is better than complex."

    print(f"Исходное изображение: {source_img}")
    print(f"Сообщение для встраивания: \"{secret_message}\"")

    # Кодирование
    encode_text_in_image(source_img, secret_message, output_img)

    # Декодирование из получившегося файла
    decoded_red = decode_text_from_image(output_img)
    print(f"\nДекодированное сообщение из красного канала: \"{decoded_red}\"")


if __name__ == '__main__':
    main()