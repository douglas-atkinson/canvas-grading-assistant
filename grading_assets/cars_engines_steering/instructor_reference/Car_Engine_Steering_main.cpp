#include "car.h"
#include "engine.h"
#include "steering.h"

#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

struct CarData {
    string id;
    string make;
    string model;
    string steeringType;
    int horsePower = 0;
    int cubicCapacity = 0;
    double wheelDiameter = 0.0;
};

void readCarData(vector<Car>& cars, const string& fileName);
CarData parseCarData(const string& line);
void printCarData(const vector<Car>& cars);

int main() {
    vector<Car> cars;
    const string fileName = "car_data.csv";

    try {
        readCarData(cars, fileName);
        printCarData(cars);
    } catch (const invalid_argument& error) {
        cerr << error.what() << '\n';
        return 1;
    }

    return 0;
}

void readCarData(vector<Car>& cars, const string& fileName) {
    ifstream file(fileName);

    if (!file.is_open()) {
        throw invalid_argument("File not found");
    }

    string dataLine;

    while (getline(file, dataLine)) {
        CarData data = parseCarData(dataLine);
        Engine engine(data.horsePower, data.cubicCapacity);
        Steering steering(data.steeringType, data.wheelDiameter);
        Car car(
            data.id,
            data.make,
            data.model,
            engine,
            steering
        );

        cars.push_back(car);
    }
}

CarData parseCarData(const string& line) {
    CarData data;
    stringstream input(line);
    string token;
    vector<string> tokens;

    while (getline(input, token, ',')) {
        tokens.push_back(token);
    }

    if (tokens.size() != 7) {
        throw invalid_argument("Invalid number of tokens");
    }

    data.id = tokens[0];
    data.make = tokens[1];
    data.model = tokens[2];
    data.horsePower = stoi(tokens[3]);
    data.cubicCapacity = stoi(tokens[4]);
    data.steeringType = tokens[5];
    data.wheelDiameter = stod(tokens[6]);

    return data;
}

void printCarData(const vector<Car>& cars) {
    for (const Car& car : cars) {
        car.print();
    }
}
