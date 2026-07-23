#include "engine.h"

#include <iostream>
#include <stdexcept>
#include <string>

int Engine::validateNonNegative(int value, const char* fieldName) {
    if (value < 0) {
        throw std::invalid_argument(
            std::string(fieldName) + " cannot be negative"
        );
    }

    return value;
}

Engine::Engine(int horsePower, int cubicCapacity)
    : horsePower(validateNonNegative(horsePower, "Horsepower")),
      cubicCapacity(validateNonNegative(cubicCapacity, "Cubic capacity")) {
}

int Engine::getHorsePower() const {
    return horsePower;
}

int Engine::getCubicCapacity() const {
    return cubicCapacity;
}

void Engine::setHorsePower(int horsePower) {
    this->horsePower = validateNonNegative(horsePower, "Horsepower");
}

void Engine::setCubicCapacity(int cubicCapacity) {
    this->cubicCapacity = validateNonNegative(
        cubicCapacity,
        "Cubic capacity"
    );
}

void Engine::print() const {
    std::cout << "        Horsepower: " << horsePower << '\n';
    std::cout << "        Cubic capacity: " << cubicCapacity << '\n';
}
