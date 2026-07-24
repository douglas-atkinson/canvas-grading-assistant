#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <stdexcept>
using namespace std;

#include "car.h"
#include "engine.h"
#include "steering.h"

// CarData struct to hold the car data
struct CarData {
	string id;
	string make;
	string model;
	string steeringType;
	int horsePower;
	int cubicCapacity;
	double wheelDiameter;
};

void readCarData(vector<Car>& cars, string fileName);
CarData parseCarData(string line);
void printCarData(const vector<Car>& cars);

int main() {
	vector<Car> cars;
	string fileName = "car_data.csv";

	try {
		readCarData(cars, fileName);
		printCarData(cars);
	} catch (const invalid_argument& e) {
		cerr << e.what() << endl;
	}
  
	return 0;
}

/// <summary>
/// This function reads the car data from a file and stores it in a vector of Car objects
/// </summary>
/// <param name="cars"></param>
/// <param name="fileName"></param>
void readCarData(vector<Car>& cars, string fileName) {
	ifstream file(fileName);

	if(!file.is_open()) {
		throw invalid_argument("File not found");
	}

	string dataLine;

	while (getline(file, dataLine)) {
		// parse the line
		CarData c = parseCarData(dataLine);
		// Create an engine object
		Engine e(c.horsePower, c.cubicCapacity);
		// Create a steering object
		Steering s(c.steeringType, c.wheelDiameter);
		// Create a car object
		Car car(c.id, c.make, c.model, e, s);
		cars.push_back(car);
	}

	file.close();
}

/// <summary>
/// This function parses a line of car data and returns a CarData object
/// </summary>
/// <param name="line"></param>
/// <returns></returns>
CarData parseCarData(string line) {
	CarData cd;				// create a CarData object
	stringstream ss(line);	// create a stringstream object
	string token;			// create a string to hold the token
	vector<string> tokens;	// create a vector to hold the tokens

	// parse the line
	while (getline(ss, token, ',')) {
		tokens.push_back(token);
	}

	// check if the number of tokens is correct
	if (tokens.size() != 7) {
		throw invalid_argument("Invalid number of tokens");
	}

	// assign the tokens to the CarData object
	cd.id = tokens[0];
	cd.make = tokens[1];
	cd.model = tokens[2];
	cd.steeringType = tokens[5];
	cd.horsePower = stoi(tokens[3]);
	cd.cubicCapacity = stoi(tokens[4]);
	cd.wheelDiameter = stod(tokens[6]);

	return cd;
}

/// <summary>
/// This function prints the car data
/// </summary>
/// <param name="cars"></param>
void printCarData(const vector<Car>& cars) {
	for (const Car& c : cars) {
		c.print();
	}
}
