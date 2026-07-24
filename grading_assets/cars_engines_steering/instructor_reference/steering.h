#ifndef STEERING_H
#define STEERING_H

#include <string>

class Steering {
public:
    Steering(const std::string& steeringType, double wheelDiameter);

    std::string getSteeringType() const;
    double getWheelDiameter() const;

    void setSteeringType(const std::string& steeringType);
    void setWheelDiameter(double wheelDiameter);

    void print() const;

private:
    static double validatePositiveDiameter(double wheelDiameter);

    std::string steeringType;
    double wheelDiameter;
};

#endif
