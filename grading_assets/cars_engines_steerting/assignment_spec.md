# Cars, Engines, and Steering

## Introduction

In this project, you will create a simple Car Management System using three
classes: `Car`, `Engine`, and `Steering`. The project provides practice with
object-oriented programming concepts, especially class composition
(a has-a relationship), encapsulation, constructors, accessors, mutators,
file processing, validation, and exception handling.

## Project Objective

Develop a Car Management System in which each `Car` object contains an
`Engine` object and a `Steering` object. The program reads car data from a
CSV file, creates the appropriate objects, and displays information about
each car.

## Required Classes

### Car Class

**Private data members**

- `id` — `string`
- `make` — `string`
- `model` — `string`
- `engine` — `Engine`
- `steering` — `Steering`

**Required methods**

- A five-parameter constructor with one parameter for each data member
- No default constructor
- Getters:
  - `getId()`
  - `getMake()`
  - `getModel()`
  - `getEngine()`
  - `getSteering()`
- Setters:
  - `setEngine()`
  - `setSteering()`
- `print()` to display the car, engine, and steering information

### Engine Class

**Private data members**

- `horsePower` — `int`
- `cubicCapacity` — `int`, measured in cubic centimeters

**Required methods**

- A two-parameter constructor
- No default constructor
- Getters:
  - `getHorsePower()`
  - `getCubicCapacity()`
- Setters:
  - `setHorsePower()`
  - `setCubicCapacity()`
- `print()` to display engine information

### Steering Class

**Private data members**

- `steeringType` — `string`, such as `"power"` or `"manual"`
- `wheelDiameter` — `double`

**Required methods**

- A two-parameter constructor
- No default constructor
- Getters:
  - `getWheelDiameter()`
  - `getSteeringType()`
- Setters:
  - `setWheelDiameter()`
  - `setSteeringType()`
- `print()` to display steering information

## CSV Data Format

The supplied data file contains one car per line using this field order:

```text
ID,Make,Model,Horsepower,CubicCapacityCC,SteeringType,WheelDiameter
```

Example rows:

```text
1001,Toyota,Corolla,132,1798,power,15.5
1002,Ford,Mustang,450,4951,manual,16
```

The file does **not** contain a header row.

Important details:

- Horsepower is stored as an integer.
- Cubic capacity is stored as an integer number of cubic centimeters.
- Wheel diameter may contain a decimal value.
- Each valid row contains exactly seven comma-separated fields.

## Project Requirements

The supplied main program demonstrates how to read and parse the CSV file.
You may keep it unchanged or modify it, provided the final program continues
to satisfy all assignment requirements.

Write the `Car`, `Engine`, and `Steering` classes according to the
specifications above. Each class must be separated into:

- one declaration file (`.h`), and
- one implementation file (`.cpp`).

The getters and setters may not all be called by the supplied main program,
but they are still required.

Use validation and exception handling where appropriate. For example,
constructors and setters should reject invalid negative numeric values rather
than silently storing them.

## Deliverables

Submit exactly seven C++ source files:

- three header files,
- three class implementation files, and
- the main program file.

Place all seven source files in a ZIP archive and submit the ZIP file through
Canvas. Do not include IDE build folders, executables, object files, or other
project artifacts.

## Evaluation Criteria

The project is evaluated in the following areas:

1. **Car Class — 50 points**
   - private data members,
   - five-parameter constructor,
   - required getters and setters,
   - required output,
   - correct composition using `Engine` and `Steering` objects.

2. **Engine Class — 40 points**
   - private data members,
   - two-parameter constructor,
   - required getters and setters,
   - required output.

3. **Steering Class — 40 points**
   - private data members,
   - two-parameter constructor,
   - required getters and setters,
   - required output.

4. **Program Correctness — 40 points**
   - compilation,
   - compatibility with the supplied main program,
   - required output,
   - correct processing and display of all cars.

5. **Code Quality and Organization — 20 points**
   - correct separation into header and implementation files,
   - readable code, meaningful names, consistent formatting, and sound
     organization.

6. **Exception Handling and Validation — 10 points**
   - appropriate validation and exceptions in constructors and setters.

The detailed scoring rules are provided in the project rubric.

## Sample Output

```text
Car: 1001 Toyota Corolla
        Horsepower: 132
        Cubic capacity: 1798
        Steering type: power
        Wheel diameter: 15.5

Car: 1002 Ford Mustang
        Horsepower: 450
        Cubic capacity: 4951
        Steering type: manual
        Wheel diameter: 16

Car: 1003 Honda Civic
        Horsepower: 158
        Cubic capacity: 1996
        Steering type: power
        Wheel diameter: 16.5

Car: 1004 Chevrolet Camaro
        Horsepower: 275
        Cubic capacity: 1998
        Steering type: manual
        Wheel diameter: 17

Car: 1005 BMW 3 Series
        Horsepower: 255
        Cubic capacity: 1998
        Steering type: power
        Wheel diameter: 16

Car: 1006 Audi A4
        Horsepower: 201
        Cubic capacity: 1984
        Steering type: power
        Wheel diameter: 17.5

Car: 1007 Mazda MX-5
        Horsepower: 181
        Cubic capacity: 1998
        Steering type: manual
        Wheel diameter: 16

Car: 1008 Subaru Impreza
        Horsepower: 152
        Cubic capacity: 1995
        Steering type: power
        Wheel diameter: 17

Car: 1009 Volkswagen Golf
        Horsepower: 147
        Cubic capacity: 1395
        Steering type: power
        Wheel diameter: 15

Car: 1010 Nissan 370Z
        Horsepower: 332
        Cubic capacity: 3696
        Steering type: manual
        Wheel diameter: 18
```
