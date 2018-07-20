#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2017 jem@seethis.link
# Licensed under the MIT license (http://opensource.org/licenses/MIT)

from __future__ import absolute_import, division, print_function, unicode_literals

import copy

# import parse_objs
import re
import sys

def sanitize_str(s):
    if s == "":
        return '""'
    for char in s:
        if char in [' ', '\n', '(', ')']:
            return '"{}"'.format(s)
    return s

def gen_indent(depth):
    return "  " * depth


def flipped_layer_str(layer_str):
        matches = re.match("([FB])\.(.*)", layer_str)
        if not matches:
            return layer_str

        layer_side = matches.group(1)
        layer_name = matches.group(2)

        layer_side = {
            'F': 'B',
            'B': 'F',
        }[layer_side]

        return layer_side + '.' + layer_name

def generate_paren_value(value):
    if isinstance(value, str):
        return sanitize_str(value)
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, (list, tuple)):
        if len(value) == 0:
            return ""
        else:
            return generate_paren_value(value[0]) + generate_paren_value(value[1:])

def generate_paren_statement(key, value):
    return "({} {})".format(key, generate_paren_value(value))


class PCBObjectTypeError(Exception):
    def __init__(self, field, got_type, want_type):
        self.field = field
        self.got_type = got_type
        self.want_type = want_type

    def __str__(self):
        print(type(self.got_type), type(self.want_type), file=sys.stderr)
        return "Expected type for field '{}' is '{}' but got a '{}'".format(
            self.field, self.want_type, self.got_type
        )

class PCBObject(object):
    pass
    # def __str__(self):
    #     return self.generate()

class PCBObjectContainer(object):
    def __init__(self):
        self.objects = []

    def __iadd__(self, obj):
        self.add_object(obj)
        return self

    def add_object(self, obj):
        self.objects.append(obj)

    def _add_token_objects(self, tokens):
        for item in tokens:
            if isinstance(item, PCBObject):
                self.objects.append(item)

    def gen_objects(self, indent_depth=0):
        iter_obj = iter(self.objects)
        # indent_str = gen_indent(indent_depth)
        indent_depth += 1
        result = next(iter_obj).generate(indent_depth=indent_depth)
        for obj in iter_obj:
            result += "\n" + obj.generate(indent_depth=indent_depth)
        return result

class PCBDocument(PCBObjectContainer):
    def __init__(self, version=4, host="pcbnew 4.0.7"):
        super(PCBDocument, self).__init__()
        self.version = version
        self.host = host
        self.general = PCBGeneral()

    def generate(self, indent_depth=0):
        # TODO: check what host field is used for
        result = "(kicad_pcb (version {version}) (host {host})\n".format(
            version = self.version,
            host = self.host
        )
        result += "\n"
        result += self.general.generate()
        result += "\n"
        result += self.gen_objects(indent_depth=indent_depth)
        result += "\n)"
        return result

class PCBGeneral(PCBObject):
    OPTION_MAP = {
        'links': int,
        'no_connects': int,
        'area': (float, float, float, float),
        'thickness': float,
        'drawings': int,
        'tracks': int,
        'zones': int,
        'modules': int,
        'nets': int,
    }

    def __init__(self, options={}):
        self._options = options

        for field in self._options:
            got_type = type(self._options[field])
            want_type = self.OPTION_MAP[field]
            if field in self.OPTION_MAP:
                type_mismatch = False
                if isinstance(want_type, (tuple, list)):
                    for (i, _) in enumerate(want_type):
                        if type(self._options[field][i]) != want_type[i]:
                            type_mismatch = True
                            break;
                else:
                    type_mismatch = (got_type != want_type)

                if type_mismatch:
                    raise PCBObjectTypeError(field, got_type, want_type)
            elif not field in self.OPTION_MAP:
                print(
                    "Warning: unknown field '{}' in 'general' object".format(
                        field
                    ),
                    file=sys.stderr
                )

    def set_thickness(self, value):
        assert(isinstance(value, (int, float)) and value > 0)
        self._options['thickness'] = value

    def generate(self):
        result = "(general \n"
        for key in self._options.keys():
            result += generate_paren_statement(key, self._options[key]) + "\n"
        result += ")"
        return result

class Page(PCBObject):
    def __init__(self, page="A4"):
        self.page = page

    def generate(self):
        return "(page {page})".format(page=self.page)

class LayerList(PCBObject):
    def __init__(self, layers=[]):
        self.layers = layers

    @staticmethod
    def kicad_default_layers():
        return LayerList(layers=[
            (0  , "F.Cu"      , "signal"),
            (31 , "B.Cu"      , "signal"),
            (32 , "B.Adhes"   , "user"),
            (33 , "F.Adhes"   , "user"),
            (34 , "B.Paste"   , "user"),
            (35 , "F.Paste"   , "user"),
            (36 , "B.SilkS"   , "user"),
            (37 , "F.SilkS"   , "user"),
            (38 , "B.Mask"    , "user"),
            (39 , "F.Mask"    , "user"),
            (40 , "Dwgs.User" , "user"),
            (41 , "Cmts.User" , "user"),
            (42 , "Eco1.User" , "user"),
            (43 , "Eco2.User" , "user"),
            (44 , "Edge.Cuts" , "user"),
            (45 , "Margin"    , "user"),
            (46 , "B.CrtYd"   , "user"),
            (47 , "F.CrtYd"   , "user"),
            (48 , "B.Fab"     , "user"),
            (49 , "F.Fab"     , "user"),
        ])

    def generate(self):
        result = "(layers\n"
        for layer in self.layers:
            result += "({number} {name} {category})\n".format(
                number   = layer[0],
                name     = sanitize_str(layer[1]),
                category = layer[2],
            )
        result += ")"
        return result

class Net(PCBObject):
    def __init__(self, number, name):
        self.number = number
        self.name = sanitize_str(name)

    def generate(self):
        return "(net {number} {name})".format(
            number = self.number,
            name = sanitize_str(self.name),
        )

class NetClass(PCBObjectContainer):
    def __init__(self, name, description):
        self.name = name
        self.description = description

        self.clearance = 0.2
        self.trace_width = 0.25

        self.via_dia = 0.6
        self.via_drill = 0.4

        self.uvia_dia = 0.3
        self.uvia_drill = 0.1

        self.objects = []

    @staticmethod
    def kicad_default_net_class():
        return NetClass("Default", "This is the default net class.")

    def add_net(self, pcb_net):
        self.add_object(pcb_net)

    def generate(self):
        result = "(net_class {name} \"{description}\"\n".format(
            name = sanitize_str(self.name),
            description = self.description,
        )
        result += "(clearance {})\n".format(self.clearance)
        result += "(trace_width {})\n".format(self.trace_width)
        result += "(via_dia {})\n".format(self.via_dia)
        result += "(via_drill {})\n".format(self.via_drill)
        result += "(uvia_dia {})\n".format(self.uvia_dia)
        result += "(uvia_drill {})\n".format(self.uvia_drill)
        result += ")"
        return result

def _bool_str(x):
    if x:
        return "yes"
    else:
        return "no"

class Setup(PCBObject):
    def __init__(self):
        self.trace_min = 0.2
        self.trace_clearance = 0.2

        self.segment_width = 0.2
        self.edge_width = 0.1

        self.zone_clearance = 0.50
        self.zone_45_only = False

        self.via_size = 0.6
        self.via_drill = 0.4
        self.via_min_size = 0.4
        self.via_min_drill = 0.3

        self.uvias_allowed = False
        self.uvia_size = 0.3
        self.uvia_drill = 0.1
        self.uvia_min_size = 0.2
        self.uvia_min_drill = 0.1

        self.aux_axis_origin = [0, 0]

    def generate(self):
        result  = "(setup\n"

        # via settings
        result += "(via_size {})\n".format(self.via_size)
        result += "(via_drill {})\n".format(self.via_drill)
        result += "(via_min_size {})\n".format(self.via_min_size)
        result += "(via_min_drill {})\n".format(self.via_min_drill)
        # μvia settings
        result += "(uvia_size {})\n".format(self.uvia_size)
        result += "(uvia_drill {})\n".format(self.uvia_drill)
        result += "(uvia_min_size {})\n".format(self.uvia_min_size)
        result += "(uvia_min_drill {})\n".format(self.uvia_min_drill)
        result += ")"
        return result

class Segment(PCBObject):
    def __init__(self, start, end, width, layer, net):
        self.start = start
        self.end = end
        self.width = width
        self.layer = layer
        self.net = net

    def generate(self):
        return "(segment {start} {end} (width {width}) (layer {layer}) (net {net}))".format(
            start = self.start.gen_start(),
            end = self.end.gen_end(),
            width = self.width,
            layer = self.layer,
            net = self.net.number
        )

class Via(PCBObject):
    def __init__(self, pos, size, drill, net, layers=["F.Cu", "B.Cu"]):
        self.pos = pos
        self.size = size
        self.drill = drill
        self.net = net
        self.layers = layers

    def generate(self):
        return "(via {pos} (size {size}) {drill} (layers {layers}) (net {net}))".format(
            pos = self.pos.generate(),
            size = self.size,
            drill = self.drill.generate(),
            layers = " ".join(self.layers),
            net = self.net.number,
        )

class Model(PCBObject):
    @staticmethod
    def from_tokens(tokens):
        result = Model()
        result.path = tokens.path
        result.pos3d = tokens.at3d[0]
        result.scale3d = tokens.scale3d[0]
        result.rotate3d = tokens.rotate3d[0]
        return result

    def __str__(self):
        return "Model({}, pos={}, scale={}, rotate={})".format(
            self.path,
            self.pos3d,
            self.scale3d,
            self.rotate3d
        )

    def generate(self, indent_depth=0):
        indent_str = gen_indent(indent_depth)
        return indent_str + "(model {path} {pos} {scale} {rotate})".format(
            path = sanitize_str(self.path),
            pos = self.pos3d.gen_pos(),
            scale = self.scale3d.gen_scale(),
            rotate = self.rotate3d.gen_rotate(),
        )

class Font(PCBObject):
    def __init__(self):
        self.size = None
        self.thickness = None

    @staticmethod
    def from_tokens(tokens):
        result = Font()
        if tokens.size:
            result.size = tokens.size[0]
        if tokens.thickness:
            result.thickness = tokens.thickness[0]
        return result

    def generate(self):
        result = "(font"
        if self.size:
            result += "  {}".format(self.size.generate())
        if self.thickness:
            result += " (thickness {})".format(self.thickness)
        result += ")"
        return result

class Effects(PCBObject):
    @staticmethod
    def from_tokens(tokens):
        result = Effects()
        if tokens.font:
            result.font = tokens.font
        else:
            result.font = None
        return result

    def generate(self):
        result = "(effects"
        if self.font:
            result += " {}".format(self.font.generate())
        result += ")"
        return result

class FP_Text(PCBObject):
    # def __init__(self, text, kind, pos, layer='F.SilkS', width=0.1):
    def __init__(self):
        pass

    @staticmethod
    def from_tokens(tokens):
        result = FP_Text()
        result.pos = tokens.at[0]
        result.kind = tokens.kind
        result.text = tokens.text
        result.layer = tokens.layer[0]
        result.effects = tokens.effects
        return result

    def generate(self, indent_depth=0):
        indent_str = gen_indent(indent_depth)
        return indent_str + "(fp_text {kind} {text} {pos} (layer {layer}) {effects})".format(
            kind = self.kind,
            text = sanitize_str(self.text),
            pos = self.pos.generate(),
            layer = self.layer,
            effects = self.effects.generate(),
        )

    def flip(self):
        new_layer = flipped_layer_str(self.layer)
        if new_layer:
            self.layer = new_layer
        self.pos.y *= -1


class LineCommon(PCBObject):
    def __init__(self, keyword, start=[0.0, 0.0], end=[0.0, 0.0], layer='F.SilkS', width=0.15):
        self.start = Pos(start[0], start[1])
        self.end = Pos(end[0], end[1])
        self.layer = layer
        self.width = width
        self._keyword = keyword

    @staticmethod
    def from_tokens(keyword, tokens):
        result = LineCommon(keyword)
        if tokens.start:
            result.start = tokens.start[0]
        else:
            result.start = Pos()
        if tokens.end:
            result.end = tokens.end[0]
        else:
            result.end = Pos()
        result.layer = tokens.layer[0]
        result.width = tokens.width[0]
        return result

    def generate(self, indent_depth=0):
        indent_str = gen_indent(indent_depth)
        return indent_str + "({keyword} {start} {end} (layer {layer}) (width {width}))".format(
            keyword = self._keyword,
            start = self.start.gen_start(),
            end = self.end.gen_end(),
            layer=self.layer,
            width=self.width,
        )

    def flip(self):
        self.layer = flipped_layer_str(self.layer)
        self.start.y *= -1
        self.end.y *= -1


    def __str__(self):
        return "{}({}, {}, {}, {})".format(self._keyword, self.start, self.end, self.layer, self.width)

class FP_Line(LineCommon):
    def __init__(self, start=[0.0,0.0], end=[0.0,0.0], layer='F.Cu', width=0.15):
        super(FP_Line, self).__init__("fp_line", start=start, end=end, layer=layer, width=width)

    @staticmethod
    def from_tokens(tokens):
        return LineCommon.from_tokens("fp_line", tokens)

class GR_Line(LineCommon):
    def __init__(self, start=[0.0,0.0], end=[0.0,0.0], layer='F.SilkS', width=0.15):
        super(GR_Line, self).__init__("gr_line", start=start, end=end, layer=layer, width=width)
        self.generate()

    @staticmethod
    def from_tokens(tokens):
        return LineCommon.from_tokens("gr_line", tokens)

class Module(PCBObjectContainer):
    def __init__(self):
        super(Module, self).__init__()
        self.description = None
        self.tags = None
        self.attr = None
        self.layer = None

    @staticmethod
    def from_tokens(tokens):
        result = Module()
        result.component = tokens.component
        if tokens.at:
            result.pos = tokens.at
        else:
            result.pos = Pos()
        if tokens.descr:
            result.description = tokens.descr[0]
        if tokens.tags:
            result.tags = tokens.tags[0]
        if tokens.attr:
            result.attr = tokens.attr[0]
        if tokens.layer:
            result.layer = tokens.layer[0]
        result._add_token_objects(tokens)
        return result

    @staticmethod
    def from_str(text):
        from pykicad.pcbnew_parser import ModuleTok
        return ModuleTok.parseString(text).module

    @staticmethod
    def from_file(file_name):
        with open(file_name, encoding="utf-8") as mod_file:
            return Module.from_str(mod_file.read())


    def generate(self, indent_depth=0):
        indent_str = gen_indent(indent_depth)
        result = "\n"
        result += indent_str + "(module {component} {pos} (layer {layer})\n".format(
            component = self.component,
            pos = self.pos.generate(),
            layer = self.layer,
        )
        indent_str = gen_indent(indent_depth+1)
        if self.description:
            result += indent_str + "(descr \"{}\")\n".format(self.description)
        if self.tags:
            result += indent_str + "(tags \"{}\")\n".format(self.tags)
        if self.attr:
            result += indent_str + "(attr {})\n".format(self.attr)
        result += self.gen_objects(indent_depth=indent_depth)
        indent_str = gen_indent(indent_depth)
        result += "\n" + indent_str + ")"
        return result

    def place(self, x, y, a=0.0, flip=False, ref="REF**"):
        result = copy.deepcopy(self)
        result.pos = Pos(x, y)

        for obj in result.objects:
            if type(obj) == FP_Text and obj.kind == "reference":
                obj.text = ref

        if flip:
            result.flip()
            a += 180.0

        if a != 0.0:
            result.set_angle(a)

        return result

    def flip(self):
        self.layer = flipped_layer_str(self.layer)

        for obj in self.objects:
            if hasattr(obj, "flip"):
                obj.flip()

    def set_angle(self, angle):
        old_angle = self.pos.a
        self.pos.a = angle

        angle_adj = angle - old_angle

        for obj in self.objects:
            if hasattr(obj, "pos"):
                obj.pos.a += angle_adj


class Drill(PCBObject):
    def __init__(self, x, y=None, offset=None):
        self.x = x
        self.y = y
        self.offset = offset

    @staticmethod
    def from_tokens(tokens):
        result = Drill(None)
        if tokens.r:
            result.x = tokens.r
        return result

    def generate(self):
        result = "(drill "
        if self.y == None: # Circular hole
            result += "{}".format(self.x)
        elif self.y != None: # Oval Hole
            result += "oval {} {}".format(self.x, self.y)
        if self.offset:
            result += " " + self.offset.generate()
        result += ")"
        return result

class PCBObjectVec(PCBObject):
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    def __getitem__(self, key):
        if key == 0:
            return self.x
        if key == 1:
            return self.y

    def __str__(self):
        return "{}({}, {})".format(type(self).__name__, self.x, self.y)
    __repr__ = __str__

class PCBObjectVec3(PCBObject):
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    def __getitem__(self, key):
        if key == 0:
            return self.x
        if key == 1:
            return self.y
        if key == 2:
            return self.z

    def __str__(self):
        return "{}({}, {}, {})".format(type(self).__name__, self.x, self.y, self.z)
    __repr__ = __str__

class Offset(PCBObjectVec):
    @staticmethod
    def from_tokens(tokens):
        return Offset(tokens[0], tokens[1])

    def generate(self):
        return "(offset {} {})".format(self.pos[0], self.pos[1])

class Pos(PCBObjectVec):
    def __init__(self, x=0.0, y=0.0, a=0.0):
        super(Pos, self).__init__(x, y)
        self.a = a

    @staticmethod
    def from_tokens(tokens):
        a = 0.0
        if len(tokens) > 2:
            a = tokens[2]
        return Pos(tokens[0], tokens[1], a)

    def generate(self):
        if self.a != 0.0:
            return "(at {} {} {})".format(self.x, self.y, self.a)
        else:
            return "(at {} {})".format(self.x, self.y)

    def gen_start(self):
        return "(start {} {})".format(self.x, self.y)

    def gen_end(self):
        return "(end {} {})".format(self.x, self.y)

    def __str__(self):
        return "Pos({}, {}, {})".format(self.x, self.y, self.a)

class Vec3(PCBObjectVec3):
    @staticmethod
    def from_tokens(tokens):
        return Vec3(tokens[0], tokens[1], tokens[2])

    def generate(self):
        return "(xyz {} {} {})".format(self.x, self.y, self.z)

    def gen_pos(self):
        return "(at {})".format(self.generate())

    def gen_scale(self):
        return "(scale {})".format(self.generate())

    def gen_rotate(self):
        return "(rotate {})".format(self.generate())

class Size(PCBObjectVec):
    @staticmethod
    def from_tokens(tokens):
        return Size(tokens[0], tokens[1])

    def generate(self):
        return "(size {} {})".format(self.x, self.y)

class RectDelta(PCBObject):
    def __init__(self, x, y):
        self.delta = [x, y]

    def generate(self):
        return "(rect_delta {} {})".format(self.delta[0], self.delta[1])

class Pad(PCBObject):
    def __init__(self):
        self.pin = ""
        self.kind = None
        self.shape = None
        self.net = None
        self.pos = None
        self.size = None
        self.drill = None
        self.layers = None
        self.rect_delta = None

    @staticmethod
    def from_tokens(tokens):
        result = Pad()
        result.pin = tokens.pin
        result.kind = tokens.kind
        result.shape = tokens.shape
        if tokens.at:
            result.pos = tokens.at[0]
        else:
            result.pos = Pos()
        if tokens.size:
            result.size = tokens.size[0]
        if tokens.drill:
            result.drill = tokens.drill
        if tokens.layers:
            result.layers = tokens.layers
        if tokens.net:
            result.net = tokens.net
        return result

    def generate(self, indent_depth=0):
        indent_str = gen_indent(indent_depth)
        result = indent_str + "(pad {pin} {kind} {shape} {pos}".format(
            pin = sanitize_str(self.pin),
            kind = self.kind,
            shape = self.shape,
            pos = self.pos.generate(),
        )
        if self.size:
            result += " " + self.size.generate()
        if self.layers:
            result += " " + "(layers {})".format(" ".join(self.layers))
        if self.rect_delta:
            result += " " + self.rect_delta.generate()
        if self.drill:
            result += " " + self.drill.generate()
        if self.net:
            result += " " + self.net.generate()
        result += ")"
        return result

    def __str__(self):
        return "Pad({}, {}, {}, {}, {}, {})".format(
            self.pin,
            self.kind,
            self.shape,
            self.pos,
            self.size,
            self.layers,
        )

    def flip(self):
        self.layers = [flipped_layer_str(s) for s in self.layers]
        self.pos.y *= -1

if __name__ == "__main__":
    smd_r = Module.from_file("test.pretty/R_0805.kicad_mod")
    switch = Module.from_file("test.pretty/Cherry_MX_Matias.kicad_mod")

    newPCB = PCBDocument()
    for i in range(5):
        for j in range(1):
            x,y = (20 + 19*i, 20 + 19*j)
            ref = "SW_{}_{}".format(i, j)
            if i == 0:
                newPCB += switch.place(x, y, ref=ref)
            if i == 1:
                newPCB += switch.place(x, y, flip=True, ref=ref)
            elif i == 2:
                newPCB += switch.place(x, y, a=45, ref=ref)
            elif i == 3:
                newPCB += switch.place(x, y, a=45, flip=True, ref=ref)
            else:
                newPCB += switch.place(x, y, ref=ref)
            # newPCB += smd_r.place(x, y+5)

    with open("test_pcb.kicad_pcb", "w", encoding="utf-8") as out_file:
        out_file.write(newPCB.generate())
