# Напишіть функцію, яка приймає рядок і повертає його довжину.
def return_length(text_row: str) -> int:
    return len(text_row.replace(' ', ''))


row = '   i   love    python    '
print(return_length(row))

# Створіть функцію, яка приймає два рядки і повертає об'єднаний рядок.
def return_merged_row(row1: str, row2: str) -> str:
    return row1 + row2


first_row = 'i programming python'
second_row = ' with a smile'
print(return_merged_row(first_row, second_row))

# Реалізуйте функцію, яка приймає число і повертає його квадрат.
def square(number: int) -> int:
    return number * number


print(square(5))

# Створіть функцію, яка приймає два числа і повертає їхню суму.
def sum_result(number1: int, number2: int) -> int:
    return number1 + number2


print(sum_result(1, 2))

# Створіть функцію яка приймає 2 числа типу int, виконує операцію ділення та повертає чілу частину і залишок.
def divide(number1: int, number2: int) -> str:
    return f'Ціла частина від ділення: {number1//number2}, залишок: {number1%number2}'


print(divide(20, 7))

# Напишіть функцію для обчислення середнього значення списку чисел.
def average(number_list: list[int]) -> float:
    return sum(number_list) / len(number_list)


print(average([1, 2, 3, 4, 5]))

# Реалізуйте функцію, яка приймає два списки і повертає список, який містить спільні елементи обох списків.
def filter_list(list1: list, list2: list) -> list:
    return list(filter(lambda x: x in list1, list2))


print(filter_list(['дабуди', 'дабудай', 'нет'], ['дабуди', 'нет', 'паровоз']))

# Створіть функцію, яка приймає словник і виводить всі ключі цього словника.
def return_keys(dictionary: dict):
    return dictionary.keys()

print(return_keys({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5}))

# Реалізуйте функцію, яка приймає два словники і повертає новий словник, який є об'єднанням обох словників.
def merge_dict(dictionary1: dict, dictionary2: dict) -> dict:
    result = {}
    result.update(dictionary1)
    result.update(dictionary2)
    return result


print(merge_dict({'a': 1, 'b': 2, 'f': 6}, {'c': 3, 'd': 4, 'e': 5}))

# Напишіть функцію, яка приймає дві множини і повертає їхнє об'єднання.
def union(set1: set, set2: set) -> set:
    return set1.union(set2)


print(union({1, 2, 3}, {4, 5}))

# Створіть функцію, яка перевіряє, чи є одна множина підмножиною іншої.
def check_subset(set1: set, set2: set) -> bool:
    return set1.issubset(set2)


print(check_subset({1, 2, 3}, {4, 5}))

# Реалізуйте функцію, яка приймає число і виводить "Парне", якщо число парне, і "Непарне", якщо непарне.
def check_even_odd(number: int) -> str:
    if number % 2 == 0:
        return 'Парне'
    return 'Непарне'


print(check_even_odd(4))

# Створіть функцію, яка приймає список чисел і повертає новий список, що містить тільки парні числа.
def check_even_odd_list(list: list[int]):
    list_of_numbers = []
    for number in list:
        if number % 2 == 0:
            list_of_numbers.append(number)
        else:
            continue
    return list_of_numbers


print(check_even_odd_list([1, 2, 3, 4, 5, 6, 10, 98]))

# Написати лямбда-функцію визначальну парне/непарне.
#
# Функція приймає параметр (число) і якщо парне, видає слово “парне”, якщо ні - то “не парне”.

check_even_odd2 = lambda number: 'Парне' if number % 2 == 0 else 'Непарне'
print(check_even_odd2(5))