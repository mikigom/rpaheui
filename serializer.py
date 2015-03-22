#!/usr/bin/env python
# coding: utf-8

try:
    import settings
    DEBUG = settings.DEBUG
except ImportError:
    DEBUG = False

import os
from const import *
try:
    from rpython.rlib.listsort import TimSort
except ImportError:
    class TimSort(object):
        def __init__(self, list):
            self.list = list

        def sort(self):
            self.list.sort()


OPCODE_NAMES = [None, None, 'div', 'add', 'mul', 'mod', 'pop', 'push', 'dup', 'sel', 'mov', None, 'cmp', None, 'brz', None, 'sub', 'swap', 'halt', 'popnum', 'popchar', 'pushnum', 'pushchar', 'brpop2', 'brpop1', 'jmp']

OP_HASOP = [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
OP_USEVAL = [0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1]
VAL_CONSTS = [0, 2, 4, 4, 2, 5, 5, 3, 5, 7, 9, 9, 7, 9, 9, 8, 4, 4, 6, 2, 4, 1, 3, 4, 3, 4, 4, 3]


VAL_NUMBER = 21
VAL_UNICODE = 27


MV_RIGHT = 0 # ㅏ
# ㅐ
MV_RIGHT2 = 2 # ㅑ
# ㅒ
MV_LEFT = 4 # ㅓ
# ㅔ
MV_LEFT2 = 6 # ㅕ
# ㅖ
MV_UP = 8 # ㅗ
# ㅘ
# ㅙ
# ㅚ
MV_UP2 = 12 # ㅛ
MV_DOWN = 13 # ㅜ
# ㅝ
# ㅞ
# ㅟ
MV_DOWN2 = 17 # ㅠ
MV_HWALL = 18 # ㅡ
MV_WALL = 19 # ㅢ
MV_VWALL = 20 # ㅣ


class Debug(object):
    ENABLED = DEBUG

    def __init__(self, primitive, serialized, code_map):
        self.primitive = primitive
        self.serialized = serialized
        self.code_map = code_map
        self.inv_map = {}
        for k, v in self.code_map.items():
            try:
                self.inv_map[v].append(k)
            except:
                self.inv_map[v] = [k]

    def show(self, pc, fp=2):
        op, value = self.serialized[pc]
        positions = self.inv_map.get(pc, [])
        if not positions:
            os.write(fp, (u'%d X %s(%s) %s\n' % (pc, OPCODE_NAMES[op], unichr(0x1100 + op), value)).encode('utf-8'))
        for position in positions:
            char = self.primitive.pane[position[0]]
            os.write(fp, (u'%d %s %s(%s) %s # %s\n' % (pc, char, OPCODE_NAMES[op], unichr(0x1100 + op), value, position)).encode('utf-8'))

    def dump(self, fp=2):
        keys = sorted(self.inv_map.keys())
        for k in keys:
            pos = self.inv_map[k]
            char = self.primitive.pane[pos[0][0]]
            os.write(fp, (u'%d %s\n' % (k, char)).encode('utf-8'))

    def storage(self, storage, selected=None):
        for i, l in enumerate(storage):
            marker = u':' if l == selected else u' '
            os.write(2, (u'%s (%d):%s' % (unichr(0x11a8 + i - 1), i, marker)).encode('utf-8'))
            os.write(2, ('%s\n' % l.list[:l.pos]))


class PrimitiveProgram(object):
    def __init__(self, text):
        self.text = text.decode('utf-8')
        self.pane = {}

        pc_row = 0
        pc_col = 0
        max_col = 0
        for char in self.text:
            if char == '\n':
                pc_row += 1
                max_col = max(max_col, pc_col)
                pc_col = 0
                continue
            if u'가' <= char <= u'힣':
                self.pane[pc_row, pc_col] = char
            pc_col += 1
        max_col = max(max_col, pc_col)

        self.max_row = pc_row
        self.max_col = max_col

    def decode(self, position):
        code = self.pane[position]
        base = ord(code) - ord(u'가')
        op_code = base / 588
        mv_code = (base / 28) % 21
        val_code = base % 28
        return op_code, mv_code, val_code

    def advance_position(self, position, direction, step=1):
        r, c = position
        d = direction
        if d == DIR_DOWN:
            r += step
            if r > self.max_row:
                r = 0
            p = r, c
            return p
        elif d == DIR_RIGHT:
            c += step
            if c > self.max_col:
                c = 0
            p = r, c
            return p
        elif d == DIR_UP:
            r -= step
            if r < 0:
                r = self.max_row
            p = r, c
            return p
        elif d == DIR_LEFT:
            c -= step
            if c < 0:
                c = self.max_col
            p = r, c
            return p
        else:
            assert False

        
DIR_DOWN = 1
DIR_RIGHT = 2
DIR_UP = -1
DIR_LEFT = -2

def dir_from_mv(mv_code, direction):
    if mv_code == MV_RIGHT:
        return DIR_RIGHT, 1
    elif mv_code == MV_RIGHT2:
        return DIR_RIGHT, 2
    elif mv_code == MV_LEFT:
        return DIR_LEFT, 1
    elif mv_code == MV_LEFT2:
        return DIR_LEFT, 2
    elif mv_code == MV_UP:
        return DIR_UP, 1
    elif mv_code == MV_UP2:
        return DIR_UP, 2
    elif mv_code == MV_DOWN:
        return DIR_DOWN, 1
    elif mv_code == MV_DOWN2:
        return DIR_DOWN, 2
    elif mv_code == MV_WALL:
        if direction == DIR_RIGHT:
            return DIR_LEFT, 1
        elif direction == DIR_LEFT:
            return DIR_RIGHT, 1
        elif direction == DIR_UP:
            return DIR_DOWN, 1
        elif direction == DIR_DOWN:
            return DIR_UP, 1
        else:
            assert False
    elif mv_code == MV_HWALL:
        if direction == DIR_UP:
            return DIR_DOWN, 1
        elif direction == DIR_DOWN:
            return DIR_UP, 1
        else:
            return direction, 1
    elif mv_code == MV_VWALL:
        if direction == DIR_RIGHT:
            return DIR_LEFT, 1
        elif direction == DIR_LEFT:
            return DIR_RIGHT, 1
        else:
            return direction, 1
    else:
        return direction, 1


class Serializer(object):
    def __init__(self):
        self.lines = []
        self.debug = None

    def compile(self, program):
        """Compile to aheui-assembly representation."""
        primitive = PrimitiveProgram(program)

        code_map = {}
        self.serialize(primitive, code_map, (0, 0), DIR_DOWN)
        self.debug = Debug(primitive, self.lines, code_map)

    def serialize(self, primitive, code_map, position, direction, depth=0):
        while True:
            if not position in primitive.pane:
                position = primitive.advance_position(position, direction)
                continue

            op, mv, val = primitive.decode(position)
            new_direction, step = dir_from_mv(mv, direction)

            if (position, direction) in code_map:
                index = code_map[position, direction]
                posdir = position, direction + 10
                code_map[position, direction + 20] = len(self.lines)
                if posdir in code_map:
                    self.lines.append((OP_JMP, code_map[posdir]))
                else:
                    self.lines.append((OP_JMP, index))
                break

            code_map[position, direction] = len(self.lines)

            direction = new_direction
            if OP_HASOP[op]:
                if op == OP_POP:
                    if val == VAL_NUMBER:
                        op = OP_POPNUM
                    elif val == VAL_UNICODE:
                        op = OP_POPCHAR
                    else:
                        pass
                elif op == OP_PUSH:
                    if val == VAL_NUMBER:
                        op = OP_PUSHNUM
                    elif val == VAL_UNICODE:
                        op = OP_PUSHCHAR
                    else:
                        pass
                else:
                    pass

                if op == OP_PUSH:
                    self.lines.append((op, VAL_CONSTS[val]))
                elif op == OP_BRZ:
                    idx = len(self.lines)
                    code_map[position, direction + 10] = idx
                    self.lines.append((OP_BRZ, -1))
                    position1 = primitive.advance_position(position, direction, step)
                    self.serialize(primitive, code_map, position1, direction, depth + 1)
                    self.lines[idx] = OP_BRZ, len(self.lines)
                    position2 = primitive.advance_position(position, -direction, step)
                    self.serialize(primitive, code_map, position2, -direction, depth + 1)
                else:
                    req_size = OP_REQSIZE[op]
                    if req_size > 0:
                        brop = OP_BRPOP1 if req_size == 1 else OP_BRPOP2
                        idx = len(self.lines)
                        code_map[position, direction + 10] = idx
                        code_map[position, direction] = idx + 1
                        self.lines.append((brop, -1))
                        if OP_USEVAL[op]:
                            self.lines.append((op, val))
                        else:
                            self.lines.append((op, -1))
                        position1 = primitive.advance_position(position, direction, step)
                        self.serialize(primitive, code_map, position1, direction, depth + 1)
                        self.lines[idx] = brop, len(self.lines)
                        position2 = primitive.advance_position(position, -direction, step)
                        self.serialize(primitive, code_map, position2, -direction, depth + 1)
                    else:
                        if OP_USEVAL[op]:
                            self.lines.append((op, val))
                        else:
                            self.lines.append((op, -1))
                            if op == OP_HALT:
                                break
            position = primitive.advance_position(position, direction, step)

    def optimize_(self, pc, stacksize, reachability):
        while pc < len(self.lines):
            assert stacksize >= 0
            op, val = self.lines[pc]
            if reachability[pc] >= 0:
                if reachability[pc] <= stacksize:
                    break
            if op == OP_BRPOP1 or op == OP_BRPOP2:
                reqsize = OP_REQSIZE[op]
                if stacksize >= reqsize:
                    pc += 1
                    continue
                else:
                    reachability[pc] = stacksize
                    self.optimize_(pc + 1, stacksize, reachability)
                    self.optimize_(val, stacksize, reachability)
                    break
            elif op == OP_BRZ:
                stacksize -= 1
                if stacksize < 0: stacksize = 0
                reachability[pc] = stacksize
                self.optimize_(pc + 1, stacksize, reachability)
                self.optimize_(val, stacksize, reachability)
                break
            elif op == OP_JMP:
                reachability[pc] = stacksize
                pc = val
            else:
                reachability[pc] = stacksize
                stacksize -= OP_STACKDEL[op]
                if stacksize < 0: stacksize = 0
                stacksize += OP_STACKADD[op]
                pc += 1
                if op == OP_SEL:
                    stacksize = 0
                elif op == OP_HALT:
                    break

    def optimize(self):
        reachability = [-1] * len(self.lines)
        self.optimize_(0, 0, reachability)

        useless_map = [0] * len(self.lines)
        count = 0
        for i, able in enumerate(reachability):
            useless_map[i] = count
            if able < 0:
                count += 1
        
        new = []
        removed = 0
        code_map = {}
        for i, (op, val) in enumerate(self.lines):
            if reachability[i] < 0:
                continue
            if op in [OP_BRZ, OP_BRPOP1, OP_BRPOP2, OP_JMP]:
                new.append((op, val - useless_map[val]))
            else:
                new.append((op, val))
            if i in self.debug.inv_map:
                keys = self.debug.inv_map[i]
                useless_count = useless_map[i]
                for key in keys:
                    code_map[key] = i - useless_count


        new_debug = Debug(self.debug.primitive, new, code_map) # wrong
        self.lines = new
        self.debug = new_debug

    def write(self, fp=1):
        for op, val in self.lines:
         
            if val >= 0: 
                p_val = chr(val & 0xff) + chr((val & 0xff00) >> 8) + chr((val & 0xff0000) >> 16)
            else:
                p_val = '\0\0\0'
            if op < 0:
                op = 256 + op
            p_op = chr(op)
            p = p_val + p_op
            assert len(p) == 4
            os.write(fp, p)
        os.write(fp, '\xff\xff\xff\xff')


    def read(self, fp=0):
        self.debug = None
        self.lines = []
        while True:
            buf = os.read(fp, 4)
            assert len(buf) == 4
            if buf == '\xff\xff\xff\xff':
                break
            val = ord(buf[0]) + (ord(buf[1]) << 8) + (ord(buf[2]) << 16)
            op = ord(buf[3])
            if op > 128:
                op -= 256
            self.lines.append((op, val))


    def dump(self, fp=1):
        for i, (op, val) in enumerate(self.lines):
            code = OPCODE_NAMES[op]
            if code is None:
                code = 'inst' + str(op)
            if val != -1:
                code_val = '%s %s' % (code, val)
            else:
                code_val = code
            if self.debug and i in self.debug.inv_map:
                debug_infos = []
                for posdir in self.debug.inv_map[i]:
                    position, direction = posdir
                    syllable = self.debug.primitive.pane[position].encode('utf-8')
                    debug_infos.append(' %s %s %d' % (syllable, position, direction))
                debug_info = ''.join(debug_infos)
            else:
                debug_info = ''
            os.write(fp, '%s\t; L%d%s\n' % (code_val, i, debug_info))
