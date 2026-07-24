#ifndef ENGINE_H
#define ENGINE_H

class Engine {
public:
    Engine(int horsePower, int cubicCapacity);

    int getHorsePower() const;
    int getCubicCapacity() const;

    void setHorsePower(int horsePower);
    void setCubicCapacity(int cubicCapacity);

    void print() const;

private:
    static int validateNonNegative(int value, const char* fieldName);

    int horsePower;
    int cubicCapacity;
};

#endif
