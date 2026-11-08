# Makefile for Voice Keyword Spotting (KWS) Firmware & Native C Driver
# Supports both ARM Cortex-M33 (cross-compilation) and Native Host testing (x86_64).

CC_HOST ?= gcc
CFLAGS_HOST = -O3 -fPIC -Wall -Wextra -std=c99
LDFLAGS_HOST = -shared -lm

# ARM Cortex-M33 Toolchain from installed STM32CubeIDE 2.0.0
ARM_TOOLCHAIN_PATH ?= /opt/st/stm32cubeide_2.0.0/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.13.3.rel1.linux64_1.0.100.202509120712/tools/bin
CC_ARM = $(ARM_TOOLCHAIN_PATH)/arm-none-eabi-gcc
CFLAGS_ARM = -mcpu=cortex-m33 -mfpu=fpv5-sp-d16 -mfloat-abi=hard -mthumb -O3 -Wall -Wextra -std=c99

SRCS = kws_mfcc.c scim_coprocessor.c kws_pipeline.c
OBJS_HOST = $(SRCS:.c=.host.o)
OBJS_ARM = $(SRCS:.c=.arm.o)

TARGET_HOST_LIB = libkws_pipeline.so
TARGET_ARM_LIB = libkws_pipeline_m33.a

.PHONY: all host arm clean

all: host

host: $(TARGET_HOST_LIB)

$(TARGET_HOST_LIB): $(SRCS)
	$(CC_HOST) $(CFLAGS_HOST) $(LDFLAGS_HOST) -o $@ $^

arm: $(TARGET_ARM_LIB)

%.arm.o: %.c
	$(CC_ARM) $(CFLAGS_ARM) -c $< -o $@

$(TARGET_ARM_LIB): $(OBJS_ARM)
	$(ARM_TOOLCHAIN_PATH)/arm-none-eabi-ar rcs $@ $^

clean:
	rm -f *.o *.so *.a
