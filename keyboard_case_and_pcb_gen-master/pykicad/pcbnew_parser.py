#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2017 jem@seethis.link
# Licensed under the MIT license (http://opensource.org/licenses/MIT)

from __future__ import absolute_import, division, print_function, unicode_literals

import pyparsing
from pyparsing import (
    Keyword, Word, Optional, Literal, White, CharsNotIn, Group,
    dblQuotedString, sglQuotedString, OneOrMore, ZeroOrMore
)

import pykicad.pcbnew_obj as pcbnew_obj

# Main identifier and keyword types
IdentifierTok = pyparsing.Word(pyparsing.alphas + '_')

IntegerTok = Optional(Literal('-')) + Word(pyparsing.nums)
IntegerTok.addParseAction(lambda toks: int("".join(toks)))

UnsignedIntTok = Word(pyparsing.nums)
UnsignedIntTok.addParseAction(lambda toks: int(toks[0]))
FloatTok = Optional(Literal('-')) + Word(pyparsing.nums) + Optional(Literal('.') + Optional(Word(pyparsing.nums)))
FloatTok.addParseAction(lambda toks: float("".join(toks)))
HexStringTok = Word(pyparsing.hexnums)
HexStringTok.addParseAction(lambda toks: int(toks[0],base=16))

UnquotedStringTok = ZeroOrMore(White()).suppress() + CharsNotIn("()\"\'" + " \r\n")
UnquotedStringTok.addParseAction(lambda toks: "".join(toks).strip())

QuotedStringTok = Group(dblQuotedString() ^ sglQuotedString())
QuotedStringTok.addParseAction(lambda toks: "".join(toks[0]).strip('"'))

AnystringTok = QuotedStringTok ^ UnquotedStringTok
LeftParenTok = Literal('(').suppress()
RightParenTok = Literal(')').suppress()

BoolTrueTok = Keyword("yes", caseless=True) | Keyword("true", caseless=True)
BoolTrueTok.addParseAction(lambda : True)
BoolFalseTok = Keyword("no", caseless=True) | Keyword("false", caseless=True)
BoolFalseTok.addParseAction(lambda : False)
BooleanTok = BoolTrueTok | BoolFalseTok

def _paren_stmt(keyword, *values, store=True):
    """
    Create a parser for a parenthesized list with an initial keyword.
    """
    # result  = LeftParenTok + Keyword(keyword, caseless=True).suppress()
    result  = LeftParenTok + Keyword(keyword, caseless=True).suppress()
    for value in values:
        result += value
    result += RightParenTok
    if store:
        return result(keyword)
    else:
        return result

def _paren_data(*values):
    result = LeftParenTok
    for value in values:
        result += value
    result += RightParenTok
    return result

def _float_param(keyword):
    return _paren_stmt(keyword, FloatTok())
def _uint_param(keyword):
    return _paren_stmt(keyword, UnsignedIntTok())
def _int_param(keyword):
    return _paren_stmt(keyword, IntegerTok())
def _hex_param(keyword):
    return _paren_stmt(keyword, HexStringTok())
def _str_param(keyword):
    return _paren_stmt(keyword, AnystringTok())
def _vec2_param(keyword, store=False):
    return _paren_stmt(keyword, FloatTok(), FloatTok(), store=store)
def _bool_param(keyword):
    return _paren_stmt(keyword, BooleanTok())

def OptionalList(*values):
    value_iter = iter(values)
    result = Optional(next(value_iter))
    for val in value_iter:
        result &= Optional(val)
    return result


# start = _paren_stmt("start", ("x",Fnum), ())
TEdit = _hex_param("tedit")
TStamp = _hex_param("tstamp")
# Point like
AtTok = _paren_stmt("at", FloatTok(), FloatTok(), Optional(FloatTok()), store=False)
AtTok.addParseAction(pcbnew_obj.Pos.from_tokens)
AtTok = Group(AtTok)("at")

StartTok = _vec2_param("start", store=False)
StartTok.addParseAction(pcbnew_obj.Pos.from_tokens)
StartTok = Group(StartTok)("start")

EndTok = _vec2_param("end", store=False)
EndTok.addParseAction(pcbnew_obj.Pos.from_tokens)
EndTok = Group(EndTok)("end")

OffsetTok =  _vec2_param("offset", store=False)
OffsetTok.addParseAction(pcbnew_obj.Offset.from_tokens)
OffsetTok = Group(OffsetTok)("offset")

SizeTok = _vec2_param("size", store=False)
SizeTok.addParseAction(pcbnew_obj.Size.from_tokens)
SizeTok = Group(SizeTok)("size")

# SizeNoGroup = _vec2_param("size", store=True)
# SizeNoGroup.addParseAction(pcbnew_obj.SizeTok.from_tokens)

Size1DTok = _paren_stmt("size", FloatTok())
Size1DTok.addParseAction(lambda tokens: pcbnew_obj.SizeTok.from_tokens(list(tokens) + [0.0]))
#
LayerTok = _str_param("layer")
WidthTok = _float_param("width")
DescrTok = _str_param("descr")
TagsTok = _str_param("tags")
AttrTok = _str_param("attr")

# DrillTok = _paren_stmt("drill",
#     Group(Keyword("oval", caseless=True) + FloatTok("x") + FloatTok()) |
#     Group(FloatTok("r")),
#     Optional(OffsetTok)
# )
DrillTok = _paren_stmt("drill", FloatTok("r"))
DrillTok.addParseAction(pcbnew_obj.Drill.from_tokens)

Solder_Mask_MarginTok = _float_param("solder_mask_margin")
Solder_Paste_MarginTok = _float_param("solder_paste_margin")
Solder_Paste_Margin_RatioTok = _float_param("solder_paste_margin_ratio")
ClearanceTok = _float_param("clearance")
Trace_WidthTok = _float_param("trace_width")
Via_DiaTokTok = _float_param("via_dia")
Via_DrillTok = _float_param("via_drill")
UVia_DiaTok = _float_param("uvia_dia")
UVia_DrillTok = _float_param("uvia_drill")
ThicknessTok = _float_param("thickness")

Add_NetTok = _str_param("add_net")
NetTok = _paren_stmt("net", UnsignedIntTok("net_num"), AnystringTok("net_name"))("net")
Net_ClassTok = _paren_stmt("net_class", AnystringTok("name") + AnystringTok("description"),
    Optional(ClearanceTok) & Optional(Trace_WidthTok) &
    Optional(Via_DiaTokTok) & Optional(Via_DrillTok) &
    Optional(UVia_DiaTok) & Optional(UVia_DrillTok),
    ZeroOrMore(Add_NetTok)
)("net_class")

PageTok = _str_param("page")
LinkCountTok = _uint_param("links")
NoConnectCountTok = _uint_param("no_connects")
AreaTok = _paren_stmt("area", FloatTok("x0"), FloatTok("y0"), FloatTok("x1"), FloatTok("y1"))
DrawingCountTok = _uint_param("drawings")
TrackCountTok = _uint_param("tracks")
ZoneCountTok = _uint_param("zones")
ModuleCountTok = _uint_param("modules")
NetCountTok = _uint_param("nets")
GeneralSettingsTok = _paren_stmt("general",
    OptionalList(LinkCountTok, NoConnectCountTok, AreaTok, DrawingCountTok, TrackCountTok,
        ZoneCountTok, ModuleCountTok, NetCountTok, ThicknessTok
    )
)

Last_Trace_WidthTok = _float_param("last_trace_width")
Trace_ClearanceTok = _float_param("trace_clearance")
Zone_ClearanceTok = _float_param("zone_clearance")
Zone_45_OnlyTok = _bool_param("zone_45_only")
Trace_MinTok = _float_param("trace_min")
Segment_WidthTok = _float_param("segment_width")
Edge_WidthTok = _float_param("edge_width")
PCB_Text_WidthTok = _float_param("pcb_text_width")
PCB_Text_SizeTok = _vec2_param("pcb_text_size")
Mod_Edge_WidthTok = _float_param("mod_edge_width")
Mod_Text_SizeTok = _vec2_param("mod_text_size")
Mod_Text_WidthTok = _float_param("mod_text_width")
Pad_SizeTok = _vec2_param("pad_size")
Pad_DrillTok = _float_param("pad_drill")
Pad_To_Mask_ClearanceTok = _float_param("pad_to_mask_clearance")
Aux_Axis_OriginTok = _vec2_param("aux_axis_origin")
Visible_ElementsTok = _hex_param("visible_elements")
Via_SizeTok = _float_param("via_size")
Via_Min_SizeTok = _float_param("via_min_size")
Via_Min_DrillTok = _float_param("via_min_drill")

UVias_AllowedTok = _bool_param("uvias_allowed")
UVia_SizeTok = _float_param("uvia_size")
UVia_Min_SizeTok = _float_param("uvia_min_size")
UVia_Min_DrillTok = _float_param("uvia_min_drill")

# PCB Plot Params
LayerSelectionTok = _uint_param("layerselection")
UseGerberExtensionsTok = _bool_param("usegerberextensions")
ExcludeEdgeLayerTok = _bool_param("excludeedgelayer")
LineWidthTok = _float_param("linewidth")
PlotFramerefTok = _bool_param("plotframeref")
ViasOnMaskTok = _bool_param("viasonmask")
ModeTok = _uint_param("mode")
UseAuxOriginTok = _bool_param("useauxorigin")
HpglPenNumberTok = _float_param("hpglpennumber")
HpglPenSpeedTok = _float_param("hpglpenspeed")
HpglPenDiameterTok = _float_param("hpglpendiameter")
HpglPenOverlayTok = _float_param("hpglpenoverlay")
PsNegativeTok = _bool_param("psnegative")
Psa4OutputTok = _bool_param("psa4output")
PlotReferenceTok = _bool_param("plotreference")
PlotValueTok = _bool_param("plotvalue")
PlotOtherTextTok = _bool_param("plotothertext")
PlotInvisibleTextTok = _bool_param("plotinvisibletext")
PadsOnSilkTok = _bool_param("padsonsilk")
SubtractMaskFromSilkTok = _bool_param("subtractmaskfromsilk")
OutputFormatTok = _uint_param("outputformat")
MirrorTok = _bool_param("mirror")
DrillShapeTok = _uint_param("drillshape")
ScaleSelectionTok = _uint_param("scaleselection")
OutputDirectoryTok = _str_param("outputdirectory")
PCBPlotParamsTok = _paren_stmt("pcbplotparams", OptionalList(
    LayerSelectionTok, UseGerberExtensionsTok, ExcludeEdgeLayerTok, LineWidthTok,
    PlotReferenceTok, ViasOnMaskTok, ModeTok, UseAuxOriginTok,
    HpglPenOverlayTok, HpglPenNumberTok, HpglPenDiameterTok, HpglPenSpeedTok,
    PsNegativeTok, Psa4OutputTok,
    PlotReferenceTok, PlotValueTok, PlotOtherTextTok, PlotInvisibleTextTok, PlotFramerefTok,
    PadsOnSilkTok, SubtractMaskFromSilkTok,
    OutputFormatTok, MirrorTok, DrillShapeTok, ScaleSelectionTok,
    OutputDirectoryTok
))

SetupTok = _paren_stmt("setup", OptionalList(
    Last_Trace_WidthTok, Trace_ClearanceTok, Zone_ClearanceTok, Zone_45_OnlyTok,
    Trace_MinTok, Segment_WidthTok, Edge_WidthTok,
    PCB_Text_WidthTok, PCB_Text_SizeTok,
    Mod_Edge_WidthTok, Mod_Text_SizeTok, Mod_Text_WidthTok,
    Pad_SizeTok, Pad_DrillTok, Pad_To_Mask_ClearanceTok,
    Aux_Axis_OriginTok, Visible_ElementsTok,
    Via_DiaTokTok, Via_DrillTok, Via_SizeTok, Via_Min_SizeTok, Via_Min_DrillTok,
    UVia_DiaTok, UVia_DrillTok, UVias_AllowedTok, UVia_SizeTok, UVia_Min_SizeTok, UVia_Min_DrillTok,
    PCBPlotParamsTok
))

LayersTok = _paren_stmt("layers", OneOrMore(AnystringTok))
LayerDefinitionTok = _paren_data(UnsignedIntTok("number") + AnystringTok("name") + IdentifierTok("kind"))
LayerListTok = _paren_stmt("layers", ZeroOrMore(LayerDefinitionTok))

# Text
JustifyTok = _str_param("justify")
FontTok = _paren_stmt("font", OptionalList(SizeTok, ThicknessTok))
FontTok.addParseAction(pcbnew_obj.Font.from_tokens)

EffectsTok = _paren_stmt("effects", OptionalList(FontTok, JustifyTok))
EffectsTok.addParseAction(pcbnew_obj.Effects.from_tokens)

FP_TextTok = _paren_stmt("fp_text", IdentifierTok("kind"), AnystringTok("text"),
                        OptionalList(AtTok, LayerTok, EffectsTok, Keyword("hide"))("parameters")
                      )("fp_text")
FP_TextTok.addParseAction(pcbnew_obj.FP_Text.from_tokens)

FP_LineTok = _paren_stmt("fp_line", StartTok, EndTok, LayerTok, WidthTok)
FP_LineTok.addParseAction(pcbnew_obj.FP_Line.from_tokens)
# PadTok related
PadTok = _paren_stmt("pad", AnystringTok("pin") + IdentifierTok("kind") + IdentifierTok("shape"),
                    OptionalList(AtTok, SizeTok, DrillTok, LayersTok, NetTok, Solder_Mask_MarginTok,
                    Solder_Paste_MarginTok, Solder_Paste_Margin_RatioTok)
)
PadTok.addParseAction(pcbnew_obj.Pad.from_tokens)
# Arc and Circles
CenterTok = _paren_stmt("center", FloatTok(), FloatTok())
AngleTok = _paren_stmt("angle", FloatTok())
GR_CircleTok = _paren_stmt("gr_circle", CenterTok, EndTok, LayerTok & WidthTok)
GR_ArcTok = _paren_stmt("gr_arc", StartTok, EndTok, AngleTok, LayerTok & WidthTok)
GR_LineTok = _paren_stmt("gr_line", StartTok, EndTok, AngleTok & LayerTok & WidthTok)
GR_LineTok.addParseAction(pcbnew_obj.GR_Line.from_tokens)

At3DTok = _paren_stmt("at", _paren_stmt("xyz", FloatTok(), FloatTok(), FloatTok(), store=False), store=False)
At3DTok.addParseAction(pcbnew_obj.Vec3.from_tokens)
At3DTok = Group(At3DTok)("at3d")

Scale3DTok = _paren_stmt("scale", _paren_stmt("xyz", FloatTok(), FloatTok(), FloatTok()))
Scale3DTok.addParseAction(pcbnew_obj.Vec3.from_tokens)
Scale3DTok = Group(Scale3DTok)("scale3d")

Rotate3DTok = _paren_stmt("rotate", _paren_stmt("xyz", FloatTok(), FloatTok(), FloatTok()))
Rotate3DTok.addParseAction(pcbnew_obj.Vec3.from_tokens)
Rotate3DTok = Group(Rotate3DTok)("rotate3d")

ModelTok = _paren_stmt("model", AnystringTok("path"), OptionalList(At3DTok, Scale3DTok , Rotate3DTok))("model")
ModelTok.addParseAction(pcbnew_obj.Model.from_tokens)

# ModuleTok = (LeftParenTok + Keyword("module") + AnystringTok("component") + CharsNotIn(""))("module")

ModuleTok = _paren_stmt("module", AnystringTok("component"),
    ZeroOrMore(LayerTok | FP_TextTok | TEdit | TStamp | AtTok | DescrTok | TagsTok |
               AttrTok | GR_LineTok | FP_LineTok | PadTok | ModelTok)
)("module")
ModuleTok.addParseAction(pcbnew_obj.Module.from_tokens)

NetNumberTok = _paren_stmt("net", UnsignedIntTok())("net_num")
ViaTok = _paren_stmt("via", OptionalList(AtTok, Size1DTok, DrillTok, LayersTok, NetNumberTok))
SegmentTok = _paren_stmt("segment",
    OptionalList(StartTok, EndTok, WidthTok, LayerTok, NetNumberTok, TStamp)
)

PCBElementTok = GR_CircleTok | GR_ArcTok | ModuleTok | ViaTok | SegmentTok | NetTok | Net_ClassTok | \
    PageTok | LayerListTok | GeneralSettingsTok | SetupTok
PCBElements = ZeroOrMore(PCBElementTok)

VersionTok = _uint_param("version")
HostTok = _paren_stmt("host", AnystringTok("name"), AnystringTok("version"))
KiCAD_PCBTok = _paren_stmt("kicad_pcb", VersionTok, HostTok, PCBElements)


if __name__ == "__main__":
    result = StartTok.parseString("(start 123.456 789)")
    print(result)
    print(result.x, result.y)
    result = FP_LineTok.parseString("(fp_line (start 1 1) (end 1 2) (layer F.Cu) (width 0.1))")
    print(result)
    print(result.start, result.end, result.layer, result.width)

    test_str = """(pad 1 thru_hole rect (at -0.95 0) (size 0.7 1.3) (drill 0.3) (layers *.Cu *.Mask) (net 2 VO))"""
    result = PadTok.parseString(test_str)
    print(result)

    test_str = """(via (at 150.7 106.1) (size 0.6) (drill 0.4) (layers F.Cu B.Cu) (net 3))"""
    result = ViaTok.parseString(test_str)
    print(result)

    test_str = """
  (net_class Default "This is the default net class."
    (clearance 0.2)
    (trace_width 0.25)
    (via_dia 0.6)
    (via_drill 0.4)
    (uvia_dia 0.3)
    (uvia_drill 0.1)
    (add_net GND)
    (add_net VI)
    (add_net VO)
  )
"""
    print("### Parsing Net_ClassTok ###")
    result = Net_ClassTok.parseString(test_str)
    print(result)

    test_str = """
  (general
    (links 3)
    (no_connects 2)
    (area 145.499999 98.399999 165 106.900002)
    (thickness 1.6)
    (drawings 2)
    (tracks 20)
    (zones 0)
    (modules 4)
    (nets 4)
  )
"""
    print("### Parsing GeneralSettingsTok ###")
    result = GeneralSettingsTok.parseString(test_str)
    print(result)



    test_str = """\
(kicad_pcb (version 4) (host pcbnew 4.0.7)
  (general
    (links 3)
    (no_connects 2)
    (area 145.499999 98.399999 165 106.900002)
    (thickness 1.6)
    (drawings 2)
    (tracks 20)
    (zones 0)
    (modules 4)
    (nets 4)
  )

    (setup
        (last_trace_width 0.254)
        (trace_clearance 0.254)
        (zone_clearance 0.2)
        (zone_45_only no)
        (trace_min 0.254)
        (segment_width 0.2)
        (edge_width 0.15)
        (via_size 0.889)
        (via_drill 0.635)
        (via_min_size 0.889)
        (via_min_drill 0.508)
        (uvia_size 0.508)
        (uvia_drill 0.127)
        (uvias_allowed no)
        (uvia_min_size 0.508)
        (uvia_min_drill 0.127)
        (pcb_text_width 0.3)
        (pcb_text_size 1.5 1.5)
        (mod_edge_width 0.15)
        (mod_text_size 1.5 1.5)
        (mod_text_width 0.15)
        (pad_size 0.0005 0.0005)
        (pad_drill 0)
        (pad_to_mask_clearance 0.2)
        (aux_axis_origin 0 0)
        (visible_elements 7FFFFFFF)
        (pcbplotparams
            (layerselection 3178497)
            (usegerberextensions true)
            (excludeedgelayer true)
            (linewidth 50000)
            (plotframeref false)
            (viasonmask false)
            (mode 1)
            (useauxorigin false)
            (hpglpennumber 1)
            (hpglpenspeed 20)
            (hpglpendiameter 15)
            (hpglpenoverlay 2)
            (psnegative false)
            (psa4output false)
            (plotreference true)
            (plotvalue true)
            (plotothertext true)
            (plotinvisibletext false)
            (padsonsilk false)
            (subtractmaskfromsilk false)
            (outputformat 1)
            (mirror false)
            (drillshape 1)
            (scaleselection 1)
            (outputdirectory "")
        )
    )

  (page A4)
  (layers
    (0 F.Cu signal)
    (31 B.Cu signal)
    (32 B.Adhes user)
    (33 F.Adhes user)
    (34 B.Paste user)
    (35 F.Paste user)
    (36 B.SilkS user)
    (37 F.SilkS user)
    (38 B.Mask user)
    (39 F.Mask user)
    (40 Dwgs.User user)
    (41 Cmts.User user)
    (42 Eco1.User user)
    (43 Eco2.User user)
    (44 Edge.Cuts user)
    (45 Margin user)
    (46 B.CrtYd user)
    (47 F.CrtYd user)
    (48 B.Fab user)
    (49 F.Fab user)
  )



    (net 0 "")
    (net 1 VI)
    (net 2 VO)
    (net 3 GND)

    (gr_circle (center 152.525 97.075) (end 153.175 96.525) (layer F.SilkS) (width 0.2))
    (gr_arc (start 154.925 97.7) (end 156 97.05) (angle 90) (layer F.SilkS) (width 0.2))

  (via (at 150.7 106.1) (size 0.6) (drill 0.4) (layers F.Cu B.Cu) (net 3))
  (segment (start 151.775001 105.024999) (end 150.7 106.1) (width 0.25) (layer F.Cu) (net 3) (tstamp 59D9A063))
  (segment (start 151.775001 102.075) (end 151.775001 105.024999) (width 0.25) (layer F.Cu) (net 3))
  (segment (start 151.775001 99.224999) (end 151.775001 102.075) (width 0.25) (layer F.Cu) (net 3) (tstamp 59D9C17F))
  (segment (start 151.8 99.2) (end 151.775001 99.224999) (width 0.25) (layer F.Cu) (net 3) (tstamp 59D9C17E))
  (via (at 151.8 99.2) (size 0.6) (drill 0.4) (layers F.Cu B.Cu) (net 3))
  (segment (start 151.8 103.4) (end 151.8 99.2) (width 0.25) (layer B.Cu) (net 3) (tstamp 59D9C16E))

  (gr_line (start 31.025 0) (end 2.5 0) (angle 90) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 31.025 4.815) (end 31.025 0) (angle 90) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 39.975 4.815) (end 31.025 4.815) (angle 90) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 39.975 0) (end 39.975 4.815) (angle 90) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 69.025 0) (end 39.975 0) (angle 90) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 69.025 4.815) (end 69.025 0) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 77.975 4.815) (end 69.025 4.815) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 77.975 0) (end 77.975 4.815) (layer Edge.Cuts) (width 0.15))
  (gr_line (start 106.5 0) (end 77.975 0) (layer Edge.Cuts) (width 0.15))

  (module Resistors_SMD:R_0805 (layer F.Cu) (tedit 59D9D2FE) (tstamp 59D9D11A)
    (at 155.225001 101.675)
    (descr "Resistor SMD 0805, reflow soldering, Vishay (see dcrcw.pdf)")
    (tags "resistor 0805")
    (attr smd)
    (pad 1 thru_hole rect (at -0.95 0) (size 0.7 1.3) (drill 0.3) (layers *.Cu *.Mask)
      (net 2 VO))
    (model ${KISYS3DMOD}/Resistors_SMD.3dshapes/R_0805.wrl
      (at (xyz 0 0 0))
      (scale (xyz 1 1 1))
      (rotate (xyz 0 0 0))
    )
  )

    (module R_0805 (layer F.Cu) (tedit 58E0A804)
    (descr "Resistor SMD 0805, reflow soldering, Vishay (see dcrcw.pdf)")
    (tags "resistor 0805")
    (attr smd)
    (fp_text reference REF** (at 0 -1.65) (layer F.SilkS)
        (effects (font (size 1 1) (thickness 0.15)))
    )
    (fp_text value R_0805 (at 0 1.75) (layer F.Fab)
        (effects (font (size 1 1) (thickness 0.15)))
    )
    (fp_text user %R (at 0 0) (layer F.Fab)
        (effects (font (size 0.5 0.5) (thickness 0.075)))
    )
    (fp_line (start -1 0.62) (end -1 -0.62) (layer F.Fab) (width 0.1))
    (fp_line (start 1 0.62) (end -1 0.62) (layer F.Fab) (width 0.1))
    (fp_line (start 1 -0.62) (end 1 0.62) (layer F.Fab) (width 0.1))
    (fp_line (start -1 -0.62) (end 1 -0.62) (layer F.Fab) (width 0.1))
    (fp_line (start 0.6 0.88) (end -0.6 0.88) (layer F.SilkS) (width 0.12))
    (fp_line (start -0.6 -0.88) (end 0.6 -0.88) (layer F.SilkS) (width 0.12))
    (fp_line (start -1.55 -0.9) (end 1.55 -0.9) (layer F.CrtYd) (width 0.05))
    (fp_line (start -1.55 -0.9) (end -1.55 0.9) (layer F.CrtYd) (width 0.05))
    (fp_line (start 1.55 0.9) (end 1.55 -0.9) (layer F.CrtYd) (width 0.05))
    (fp_line (start 1.55 0.9) (end -1.55 0.9) (layer F.CrtYd) (width 0.05))
    (pad 1 smd rect (at -0.95 0) (size 0.7 1.3) (layers F.Cu F.Paste F.Mask))
    (pad 2 smd rect (at 0.95 0) (size 0.7 1.3) (layers F.Cu F.Paste F.Mask))
    (model ${KISYS3DMOD}/Resistors_SMD.3dshapes/R_0805.wrl
        (at (xyz 0 0 0))
        (scale (xyz 1 1 1))
        (rotate (xyz 0 0 0))
    )
    )


)
"""
    print("### Parsing KiCAD_PCBTok ###")
    result = KiCAD_PCBTok.parseString(test_str)
    print(result)
    print(result.setup.via_size.value)
    # print(result.model)
