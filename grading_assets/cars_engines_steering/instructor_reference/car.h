#ifndef CAR_H
#define CAR_H

#include "engine.h"
#include "steering.h"

#include <string>

class Car {
public:
    Car(
        const std::string& id,
        const std::string& make,
        const std::string& model,
        const Engine& engine,
        const Steering& steering
    );

    std::string getId() const;
    std::string getMake() const;
    std::string getModel() const;
    Engine getEngine() const;
    Steering getSteering() const;

    void setEngine(const Engine& engine);
    void setSteering(const Steering& steering);

    void print() const;

private:
    std::string id;
    std::string make;
    std::string model;
    Engine engine;
    Steering steering;
};

#endif
