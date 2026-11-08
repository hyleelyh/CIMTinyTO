# ==============================================================================
# Makefile — Tier 3 Compiled C & ARM NEON Acceleration Library for CIMTinyTO
# Target: libscim_tier3_accel.so (Shared Library for Python CFFI/ctypes)
# ==============================================================================

CC ?= gcc
CFLAGS ?= -O3 -Wall -Wextra -fPIC -std=c99
LDFLAGS ?= -shared

# Detect CPU architecture for platform-specific SIMD optimizations
UNAME_M := $(shell uname -m)

ifeq ($(findstring arm,$(UNAME_M)),arm)
    # 32-bit ARM Cortex-A9 (PYNQ-Z2 Zynq-7020)
    CFLAGS += -march=armv7-a -mfpu=neon -mfloat-abi=hard
else ifeq ($(findstring aarch64,$(UNAME_M)),aarch64)
    # 64-bit ARM (Raspberry Pi 5 / Jetson)
    CFLAGS += -march=armv8-a
else
    # x86-64 Host (Desktop PC juliusli / CI)
    CFLAGS += -mavx2 -mfma
endif

TARGET = libscim_tier3_accel.so
SRC = scim_tier3_accel.c
OBJ = scim_tier3_accel.o

all: $(TARGET)

$(OBJ): $(SRC) scim_tier3_accel.h
	$(CC) $(CFLAGS) -c $(SRC) -o $(OBJ)

$(TARGET): $(OBJ)
	$(CC) $(LDFLAGS) -o $(TARGET) $(OBJ)

clean:
	rm -f $(OBJ) $(TARGET)

.PHONY: all clean
