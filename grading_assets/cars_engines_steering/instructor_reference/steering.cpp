#include "steering.h"

#include <iostream>
#include <stdexcept>
#include <string>

double Steering::validatePositiveDiameter(double wheelDiameter) {
    if (wheelDiameter <= 0.0) {
        throw std::invalid_argument(
            "Wheel diameter must be positive"
        );
    }

    return wheelDiameter;
}

Steering::Steering(
    const std::string& steeringType,
    double wheelDiameter
)
    : steeringType(steeringType),
      wheelDiameter(validatePositiveDiameter(wheelDiameter)) {
}

std::string Steering::getSteeringType() const {
    return steeringType;
}

double Steering::getWheelDiameter() const {
    return wheelDiameter;
}

void Steering::setSteeringType(const std::string& steeringType) {
    this->steeringType = steeringType;
}

void Steering::setWheelDiameter(double wheelDiameter) {
    this->wheelDiameter = validatePositiveDiameter(wheelDiameter);
}

void Steering::print() const {
    std::cout << "        Steering type: " << steeringType << '\n';
    std::cout << "        Wheel diameter: " << wheelDiameter << '\n';
}
