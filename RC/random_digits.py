import random


# this script creates a random combination of 6 letters and numbers to add to the ids of the client's orders
class Digits:
    def __init__(self):
        self.digits = ""

    def create_new(self):
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's',
                   't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
                   'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
        numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

        random.shuffle(letters)
        random.shuffle(numbers)

        new_digits = []

        for i in range(3):
            new_digits.append(random.choice(letters))
        for i in range(3):
            new_digits.append(random.choice(numbers))

        random.shuffle(new_digits)
        final = ''.join(new_digits)

        self.digits = final
        return final
