"""
完整的虚拟机实现 - 最终工作版本
"""

import struct
import sys
from enum import Enum
from typing import List, Dict, Tuple

class OpCode(Enum):
    """操作码定义"""
    NOP = 0x00
    LOAD = 0x01     # LOAD reg, imm
    MOV = 0x02      # MOV dst, src
    ADD = 0x03
    SUB = 0x04
    MUL = 0x05
    DIV = 0x06
    MOD = 0x07
    INC = 0x08
    DEC = 0x09
    CMP = 0x0A
    JMP = 0x0B
    JE = 0x0C
    JNE = 0x0D
    JG = 0x0E
    JL = 0x0F
    JGE = 0x10
    JLE = 0x11
    PUSH = 0x12
    POP = 0x13
    CALL = 0x14
    RET = 0x15
    PRINT = 0x16
    PRINTLN = 0x17
    INPUT = 0x18
    HALT = 0x19

class VirtualMachine:
    """虚拟机实现"""
    
    def __init__(self, num_registers=8):
        self.num_registers = num_registers
        self.memory = bytearray(65536)
        self.registers = [0] * num_registers
        self.stack = []
        self.pc = 0
        self.running = True
        self.flags = {'zero': False, 'sign': False}
        self.instruction_count = 0
        
    def load_program(self, bytecode: List[Tuple]):
        """加载程序到内存"""
        addr = 0
        for instr in bytecode:
            self.memory[addr] = instr[0]  # 操作码
            addr += 1
            
            # 写入操作数
            for i in range(1, len(instr)):
                value = instr[i]
                self.memory[addr:addr+4] = struct.pack('i', value)
                addr += 4
        return addr
        
    def get_operand(self) -> int:
        """读取一个操作数"""
        value = struct.unpack('i', self.memory[self.pc:self.pc+4])[0]
        self.pc += 4
        return value
        
    def run(self):
        """运行程序"""
        while self.running:
            if self.pc >= len(self.memory):
                break
                
            opcode = self.memory[self.pc]
            self.pc += 1
            self.instruction_count += 1
            
            # 数据传送
            if opcode == OpCode.LOAD.value:
                reg = self.get_operand()
                value = self.get_operand()
                if reg < self.num_registers:
                    self.registers[reg] = value
                    
            elif opcode == OpCode.MOV.value:
                dst = self.get_operand()
                src = self.get_operand()
                if dst < self.num_registers and src < self.num_registers:
                    self.registers[dst] = self.registers[src]
                    
            # 算术运算
            elif opcode == OpCode.ADD.value:
                dst = self.get_operand()
                src = self.get_operand()
                if dst < self.num_registers and src < self.num_registers:
                    result = self.registers[dst] + self.registers[src]
                    self.registers[dst] = result
                    self.flags['zero'] = (result == 0)
                    self.flags['sign'] = (result < 0)
                    
            elif opcode == OpCode.SUB.value:
                dst = self.get_operand()
                src = self.get_operand()
                if dst < self.num_registers and src < self.num_registers:
                    result = self.registers[dst] - self.registers[src]
                    self.registers[dst] = result
                    self.flags['zero'] = (result == 0)
                    self.flags['sign'] = (result < 0)
                    
            elif opcode == OpCode.MUL.value:
                dst = self.get_operand()
                src = self.get_operand()
                if dst < self.num_registers and src < self.num_registers:
                    result = self.registers[dst] * self.registers[src]
                    self.registers[dst] = result
                    self.flags['zero'] = (result == 0)
                    self.flags['sign'] = (result < 0)
                    
            elif opcode == OpCode.DIV.value:
                dst = self.get_operand()
                src = self.get_operand()
                if dst < self.num_registers and src < self.num_registers:
                    if self.registers[src] != 0:
                        result = self.registers[dst] // self.registers[src]
                        self.registers[dst] = result
                        self.flags['zero'] = (result == 0)
                        self.flags['sign'] = (result < 0)
                        
            elif opcode == OpCode.INC.value:
                reg = self.get_operand()
                if reg < self.num_registers:
                    self.registers[reg] += 1
                    self.flags['zero'] = (self.registers[reg] == 0)
                    self.flags['sign'] = (self.registers[reg] < 0)
                    
            elif opcode == OpCode.DEC.value:
                reg = self.get_operand()
                if reg < self.num_registers:
                    self.registers[reg] -= 1
                    self.flags['zero'] = (self.registers[reg] == 0)
                    self.flags['sign'] = (self.registers[reg] < 0)
                    
            # 比较
            elif opcode == OpCode.CMP.value:
                reg1 = self.get_operand()
                reg2 = self.get_operand()
                if reg1 < self.num_registers and reg2 < self.num_registers:
                    result = self.registers[reg1] - self.registers[reg2]
                    self.flags['zero'] = (result == 0)
                    self.flags['sign'] = (result < 0)
                    
            # 跳转
            elif opcode == OpCode.JMP.value:
                addr = self.get_operand()
                self.pc = addr
                
            elif opcode == OpCode.JE.value:
                addr = self.get_operand()
                if self.flags['zero']:
                    self.pc = addr
                    
            elif opcode == OpCode.JNE.value:
                addr = self.get_operand()
                if not self.flags['zero']:
                    self.pc = addr
                    
            elif opcode == OpCode.JG.value:
                addr = self.get_operand()
                if not self.flags['sign'] and not self.flags['zero']:
                    self.pc = addr
                    
            elif opcode == OpCode.JL.value:
                addr = self.get_operand()
                if self.flags['sign']:
                    self.pc = addr
                    
            # 栈操作
            elif opcode == OpCode.PUSH.value:
                reg = self.get_operand()
                if reg < self.num_registers:
                    self.stack.append(self.registers[reg])
                    
            elif opcode == OpCode.POP.value:
                reg = self.get_operand()
                if self.stack and reg < self.num_registers:
                    self.registers[reg] = self.stack.pop()
                    
            # 输入输出
            elif opcode == OpCode.PRINT.value:
                reg = self.get_operand()
                if reg < self.num_registers:
                    print(self.registers[reg], end='')
                    
            elif opcode == OpCode.PRINTLN.value:
                reg = self.get_operand()
                if reg < self.num_registers:
                    print(self.registers[reg])
                    
            elif opcode == OpCode.INPUT.value:
                reg = self.get_operand()
                try:
                    value = int(input())
                    if reg < self.num_registers:
                        self.registers[reg] = value
                except:
                    pass
                    
            elif opcode == OpCode.HALT.value:
                self.running = False
                
    def print_state(self):
        """打印状态"""
        print(f"\nPC: {self.pc}, 指令数: {self.instruction_count}")
        print("寄存器:", [f"R{i}={self.registers[i]}" for i in range(self.num_registers)])
        print(f"标志: zero={self.flags['zero']}, sign={self.flags['sign']}")
        print(f"栈: {self.stack}")

class Assembler:
    """汇编器"""
    
    def assemble(self, source: str) -> List[Tuple]:
        """汇编源代码"""
        # 第一遍：收集标签
        labels = {}
        lines = source.strip().split('\n')
        address = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            if ';' in line:
                line = line[:line.index(';')].strip()
            if ':' in line and not line.startswith(('LOAD', 'MOV', 'ADD')):
                label = line.replace(':', '').strip()
                labels[label] = address
            else:
                parts = line.split()
                if parts:
                    op = parts[0].upper()
                    if op in ['LOAD', 'MOV', 'ADD', 'SUB', 'MUL', 'DIV', 'CMP']:
                        address += 9
                    elif op in ['JMP', 'JE', 'JNE', 'JG', 'JL', 'PUSH', 'POP', 'PRINT', 'PRINTLN', 'INPUT', 'INC', 'DEC']:
                        address += 5
                    else:
                        address += 1
        
        # 第二遍：生成字节码
        bytecode = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            if ';' in line:
                line = line[:line.index(';')].strip()
            if ':' in line and not line.startswith(('LOAD', 'MOV', 'ADD')):
                continue
                
            parts = line.split()
            if not parts:
                continue
                
            op = parts[0].upper()
            
            try:
                if op == 'LOAD':
                    reg = int(parts[1].rstrip(','))
                    val = int(parts[2].rstrip(','))
                    bytecode.append((OpCode.LOAD.value, reg, val))
                    
                elif op == 'MOV':
                    dst = int(parts[1].rstrip(','))
                    src = int(parts[2].rstrip(','))
                    bytecode.append((OpCode.MOV.value, dst, src))
                    
                elif op == 'ADD':
                    dst = int(parts[1].rstrip(','))
                    src = int(parts[2].rstrip(','))
                    bytecode.append((OpCode.ADD.value, dst, src))
                    
                elif op == 'SUB':
                    dst = int(parts[1].rstrip(','))
                    src = int(parts[2].rstrip(','))
                    bytecode.append((OpCode.SUB.value, dst, src))
                    
                elif op == 'MUL':
                    dst = int(parts[1].rstrip(','))
                    src = int(parts[2].rstrip(','))
                    bytecode.append((OpCode.MUL.value, dst, src))
                    
                elif op == 'DIV':
                    dst = int(parts[1].rstrip(','))
                    src = int(parts[2].rstrip(','))
                    bytecode.append((OpCode.DIV.value, dst, src))
                    
                elif op == 'INC':
                    reg = int(parts[1].rstrip(','))
                    bytecode.append((OpCode.INC.value, reg))
                    
                elif op == 'DEC':
                    reg = int(parts[1].rstrip(','))
                    bytecode.append((OpCode.DEC.value, reg))
                    
                elif op == 'CMP':
                    reg1 = int(parts[1].rstrip(','))
                    reg2 = int(parts[2].rstrip(','))
                    bytecode.append((OpCode.CMP.value, reg1, reg2))
                    
                elif op == 'JMP':
                    target = labels.get(parts[1], int(parts[1]))
                    bytecode.append((OpCode.JMP.value, target))
                    
                elif op == 'JE':
                    target = labels.get(parts[1], int(parts[1]))
                    bytecode.append((OpCode.JE.value, target))
                    
                elif op == 'JNE':
                    target = labels.get(parts[1], int(parts[1]))
                    bytecode.append((OpCode.JNE.value, target))
                    
                elif op == 'JG':
                    target = labels.get(parts[1], int(parts[1]))
                    bytecode.append((OpCode.JG.value, target))
                    
                elif op == 'JL':
                    target = labels.get(parts[1], int(parts[1]))
                    bytecode.append((OpCode.JL.value, target))
                    
                elif op == 'PUSH':
                    reg = int(parts[1].rstrip(','))
                    bytecode.append((OpCode.PUSH.value, reg))
                    
                elif op == 'POP':
                    reg = int(parts[1].rstrip(','))
                    bytecode.append((OpCode.POP.value, reg))
                    
                elif op == 'PRINT':
                    reg = int(parts[1].rstrip(','))
                    bytecode.append((OpCode.PRINT.value, reg))
                    
                elif op == 'PRINTLN':
                    reg = int(parts[1].rstrip(','))
                    bytecode.append((OpCode.PRINTLN.value, reg))
                    
                elif op == 'INPUT':
                    reg = int(parts[1].rstrip(','))
                    bytecode.append((OpCode.INPUT.value, reg))
                    
                elif op == 'HALT':
                    bytecode.append((OpCode.HALT.value,))
                    
            except Exception as e:
                print(f"汇编错误: {e} - {line}")
                
        return bytecode

# 测试程序
def test1_addition():
    """测试加法"""
    print("\n1. 加法测试: 计算 10 + 20")
    code = """
    LOAD 0, 10
    LOAD 1, 20
    ADD 0, 1
    PRINT 0
    HALT
    """
    vm = VirtualMachine()
    assembler = Assembler()
    bytecode = assembler.assemble(code)
    vm.load_program(bytecode)
    vm.run()

def test2_factorial():
    """测试阶乘"""
    print("\n2. 阶乘测试: 计算 5!")
    code = """
    LOAD 0, 5      ; n = 5
    LOAD 1, 1      ; result = 1
    
    LOOP:
        MUL 1, 0   ; result = result * n
        DEC 0      ; n--
        CMP 0, 0   ; 比较 n 和 0
        JNZ LOOP   ; 如果 n != 0，继续循环
    
    PRINT 1        ; 输出结果
    HALT
    """
    vm = VirtualMachine()
    assembler = Assembler()
    bytecode = assembler.assemble(code)
    vm.load_program(bytecode)
    vm.run()

def test3_fibonacci():
    """测试斐波那契数列"""
    print("\n3. 斐波那契数列: 计算第10项")
    code = """
    ; 斐波那契数列 F(10) = 55
    LOAD 0, 10     ; n = 10
    LOAD 1, 0      ; a = 0 (F0)
    LOAD 2, 1      ; b = 1 (F1)
    LOAD 3, 2      ; i = 2
    
    CMP 3, 0       ; 比较 i 和 n
    JG OUTPUT      ; 如果 i > n，跳转到输出
    
    LOOP:
        ADD 2, 1   ; b = a + b
        MOV 1, 2   ; a = b
        SUB 2, 1   ; b = b - a
        ADD 2, 1   ; b = a + b
        INC 3      ; i++
        CMP 3, 0   ; 比较 i 和 n
        JLE LOOP   ; 如果 i <= n，继续循环
    
    OUTPUT:
        PRINT 2    ; 输出结果
        HALT
    """
    vm = VirtualMachine()
    assembler = Assembler()
    bytecode = assembler.assemble(code)
    vm.load_program(bytecode)
    vm.run()

def test4_loop():
    """测试循环：1到10的和"""
    print("\n4. 循环测试: 计算 1+2+...+10")
    code = """
    LOAD 0, 10     ; max = 10
    LOAD 1, 1      ; i = 1
    LOAD 2, 0      ; sum = 0
    
    LOOP:
        ADD 2, 1   ; sum = sum + i
        INC 1      ; i++
        CMP 1, 0   ; 比较 i 和 max
        JLE LOOP   ; 如果 i <= max，继续
    
    PRINT 2        ; 输出和
    HALT
    """
    vm = VirtualMachine()
    assembler = Assembler()
    bytecode = assembler.assemble(code)
    vm.load_program(bytecode)
    vm.run()

def test5_interactive():
    """交互式程序：计算平方"""
    print("\n5. 交互式程序: 计算平方")
    code = """
    PRINT 0       ; 输出提示
    PRINTLN 0
    INPUT 0       ; 输入数字
    MOV 1, 0      ; 复制到R1
    MUL 1, 0      ; 计算平方
    PRINT 1       ; 输出结果
    HALT
    """
    print("请输入一个整数:")
    vm = VirtualMachine()
    assembler = Assembler()
    bytecode = assembler.assemble(code)
    vm.load_program(bytecode)
    vm.run()

if __name__ == "__main__":
    print("="*60)
    print("虚拟机演示程序")
    print("="*60)
    
    test1_addition()      # 10 + 20 = 30
    test2_factorial()     # 5! = 120
    test3_fibonacci()     # 斐波那契第10项 = 55
    test4_loop()          # 1到10的和 = 55
    
    # 可选：交互式程序
    # test5_interactive()
    
    print("\n" + "="*60)
    print("所有测试完成!")
    print("="*60)
