# ==============================================================================
# Makefile — Tier 2 Compiled C MMIO Driver for CIMTinyTO
# Target: libscim_tier2.so (Shared Library for Python CFFI/ctypes)
# ==============================================================================

CC ?= gcc
CFLAGS ?= -O3 -Wall -Wextra -fPIC -std=c99
LDFLAGS ?= -shared

TARGET = libscim_tier2.so
SRC = scim_tier2_driver.c
OBJ = scim_tier2_driver.o

all: $(TARGET)

$(OBJ): $(SRC) scim_tier2_driver.h
	$(CC) $(CFLAGS) -c $(SRC) -o $(OBJ)

$(TARGET): $(OBJ)
	$(CC) $(LDFLAGS) -o $(TARGET) $(OBJ)

clean:
	rm -f $(OBJ) $(TARGET)

.PHONY: all clean
