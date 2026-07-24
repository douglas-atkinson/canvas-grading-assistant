#include "car.h"

#include <iostream>
#include <string>

Car::Car(
    const std::string& id,
    const std::string& make,
    const std::string& model,
    const Engine& engine,
    const Steering& steering
)
    : id(id),
      make(make),
      model(model),
      engine(engine),
      steering(steering) {
}

std::string Car::getId() const {
    return id;
}

std::string Car::getMake() const {
    return make;
}

std::string Car::getModel() const {
    return model;
}

Engine Car::getEngine() const {
    return engine;
}

Steering Car::getSteering() const {
    return steering;
}

void Car::setEngine(const Engine& engine) {
    this->engine = engine;
}

void Car::setSteering(const Steering& steering) {
    this->steering = steering;
}

void Car::print() const {
    std::cout << "Car: " << id << ' ' << make << ' ' << model << '\n';
    engine.print();
    steering.print();
    std::cout << '\n';
}
