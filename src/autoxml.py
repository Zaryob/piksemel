#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2007, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version. Please read the COPYING file.
#

import piksemel
import inspect
import locale

# Global counter for keeping tag order
_autoPiksCounter = 0

# Enumerations
multiple, optional = range(1, 3)


class InvalidDocument(Exception):
    """Validation error while reading XML data."""
    pass


class CharacterData:
    """Maps character data of the XML node into a variable."""
    def parse(self, ctx, doc):
        node = doc.firstChild()
        if node.type() != piksemel.DATA or node.next() != None:
            ctx.error("this tag should only contain character data")
        else:
            ctx.use(self.varname, node.data())
    
    def serialize(self, inst, doc):
        doc.insertData(getattr(inst, self.varname))


class Attribute:
    """Maps an attribute of the XML node into a variable."""
    def __init__(self, attrname, *args):
        self.name = attrname
        self.is_optional = False
        self.choices = None
        for arg in args:
            if arg == optional:
                self.is_optional = True
            elif isinstance(arg, (tuple, list)):
                self.choices = arg
            else:
                raise TypeError("Unknown argument '%s'" % arg)
    
    def parse(self, ctx, doc):
        value = doc.getAttribute(self.name)
        if not self.is_optional and value == None:
            ctx.error("required attribute '%s' is missing" % self.name)
        if value and self.choices and not value in self.choices:
            ctx.error("keyword '%s' is not accepted for attribute '%s'" % (value, self.name))
        ctx.use(self.varname, value)
    
    def serialize(self, inst, doc):
        val = getattr(inst, self.varname)
        if val:
            doc.setAttribute(self.name, unicode(val))


class Tag:
    """Maps a child tag's data of the XML node into a variable."""
    def __init__(self, tagname, *args):
        global _autoPiksCounter
        self.order = _autoPiksCounter
        _autoPiksCounter += 1
        self.name = tagname
        self.is_optional = False
        self.is_multiple = False
        self.sub = None
        for arg in args:
            if arg == optional:
                self.is_optional = True
            elif arg == multiple:
                self.is_multiple = True
            elif issubclass(arg, AutoXML):
                self.sub = arg
            else:
                raise TypeError("Unknown argument '%s'" % arg)
    
    def parse(self, ctx, doc):
        tags = list(doc.tags(self.name))
        if not self.is_optional and len(tags) == 0:
            ctx.error("missing tag <%s>" % self.name)
            return
        if not self.is_multiple and len(tags) > 1:
            ctx.error("tag <%s> should not appear more than once" % self.name)
            return
        old_doc = ctx.doc
        vals = []
        for tag in tags:
            ctx.doc = tag
            if self.sub:
                c = self.sub()
                old_inst = ctx.inst
                ctx.inst = c
                c._autoPiksParse(ctx, tag)
                ctx.inst = old_inst
                vals.append(c)
            else:
                node = tag.firstChild()
                if node.type() != piksemel.DATA or node.next() != None:
                    ctx.error("this tag should only contain character data")
                else:
                    vals.append(node.data())
        if not self.is_multiple:
            if len(vals) > 0:
                vals = vals[0]
            else:
                vals = None
        ctx.use(self.varname, vals)
        ctx.doc = old_doc
        
    def serialize(self, inst, doc):
        vals = getattr(inst, self.varname)
        if not vals:
            return
        if not self.is_multiple:
            vals = [vals]
        for val in vals:
            tag = doc.insertTag(self.name)
            if self.sub:
                val.toString(tag)
            else:
                if val:
                    tag.insertData(val)


class TagCollection:
    """Maps a collection of child tags of the XML node into a variable."""
    def __init__(self, tagname, kidname, *args):
        global _autoPiksCounter
        self.order = _autoPiksCounter
        _autoPiksCounter += 1
        self.name = tagname
        self.kidname = kidname
        self.is_optional = False
        self.sub = None
        for arg in args:
            if arg == optional:
                self.is_optional = True
            elif issubclass(arg, AutoXML):
                self.sub = arg
            else:
                raise TypeError("Unknown argument '%s'" % arg)
    
    def parse(self, ctx, doc):
        tags = list(doc.tags(self.name))
        if len(tags) == 0:
            if not self.is_optional:
                ctx.error("missing tag <%s>" % self.name)
            ctx.use(self.varname, [])
            return
        if len(tags) > 1:
            ctx.error("tag <%s> should not appear more than once" % self.name)
            return
        tags = list(tags[0].tags())
        old_doc = ctx.doc
        vals = []
        for tag in tags:
            ctx.doc = tag
            if tag.name() != self.kidname:
                ctx.error("this is a collection of <%s> tags, not <%s>" % (self.kidname, tag.name()))
            if self.sub:
                c = self.sub()
                old_inst = ctx.inst
                ctx.inst = c
                c._autoPiksParse(ctx, tag)
                ctx.inst = old_inst
                vals.append(c)
            else:
                node = tag.firstChild()
                if node.type() != piksemel.DATA or node.next() != None:
                    ctx.error("this tag should only contain character data")
                else:
                    vals.append(node.data())
        ctx.use(self.varname, vals)
        ctx.doc = old_doc
    
    def serialize(self, inst, doc):
        vals = getattr(inst, self.varname)
        if not vals:
            return
        parent = doc.insertTag(self.name)
        for val in vals:
            tag = parent.insertTag(self.kidname)
            if self.sub:
                val.toString(tag)
            else:
                if val:
                    tag.insertData(val)


class LocalText(dict):
    @staticmethod
    def get_lang():
        lang, enc = locale.getlocale()
        if not lang:
            lang, enc = locale.getdefaultlocale()
        if not lang:
            return "en"
        return lang[:2]
    
    def __str__(self):
        lang = self.get_lang()
        # Return text for current language
        t = self.get(lang, None)
        if t:
            return t
        # Fallback to English
        t = self.get("en", None)
        if t:
            return t
        # Fallback to anything
        if len(self) > 0:
            return self[0]
        return str()


class TagLocalized:
    """Maps the translated tags of the XML node into a dictionary variable."""
    def __init__(self, tagname, opt=None):
        global _autoPiksCounter
        self.order = _autoPiksCounter
        _autoPiksCounter += 1
        self.name = tagname
        self.is_optional = False
        if opt == optional:
            self.is_optional = True
    
    def parse(self, ctx, doc):
        tags = list(doc.tags(self.name))
        if not self.is_optional and len(tags) == 0:
            ctx.error("missing tag <%s>" % self.name)
            return
        val = LocalText()
        for tag in tags:
            lang = tag.getAttribute("xml:lang")
            if not lang:
                lang = "en"
            node = tag.firstChild()
            if node.type() != piksemel.DATA or node.next() != None:
                ctx.error("%s: Localized tag should only contain character data" % self.name)
            else:
                if val.has_key(lang):
                    ctx.error("%s: Duplicate translation for language %s" % (self.name, lang))
                data = node.data()
                val[lang] = data
        ctx.use(self.varname, val)
    
    def serialize(self, inst, doc):
        val = getattr(inst, self.varname)
        if not val:
            return
        langs = val.keys()
        langs.sort()
        for lang in langs:
            tag = doc.insertTag(self.name)
            if lang != "en":
                tag.setAttribute("xml:lang", lang)
            tag.insertData(val[lang])


class AutoPiksemelContext:
    """Utility class for passing parameters between validation functions."""
    def __init__(self, inst):
        self.inst = inst
        self.errors = []
        self.doc = None
    
    def error(self, message):
        path = []
        doc = self.doc
        while doc:
            path.append(doc.name())
            doc = doc.parent()
        path.reverse()
        self.errors.append("%s: %s" % ("/".join(path), message))
    
    def use(self, varname, value):
        setattr(self.inst, varname, value)


class AutoXML:
    """Automatic XML <-> Class attributes converter with validation."""
    def __init__(self, root_tag=None, path=None, xmlstring=None):
        self.root_tag = root_tag
        doc = None
        if path:
            if xmlstring:
                raise TypeError("Dont use both path and xmlstring in AutoPiksemel()")
            doc = piksemel.parse(path)
        elif xmlstring:
            doc = piksemel.parseString(xmlstring)
        if doc:
            if doc.name() != root_tag:
                err = "Root tag does not match: %s != %s" % (root_tag, doc.name())
                raise InvalidDocument(err)
            ctx = AutoPiksemelContext(self)
            ctx.doc = doc
            self._autoPiksParse(ctx, doc)
            if len(ctx.errors) > 0:
                raise InvalidDocument("\n".join(ctx.errors))
    
    def _autoPiksScan(self):
        """Scan XML<->Class mappings and return indexed objects."""
        # Generated data is cached as a Class variable
        defs = getattr(self.__class__, "_autoPiksDefs", None)
        if not defs:
            members = inspect.getmembers(self.__class__)
            cdata = None
            attrs = {}
            tags = {}
            for name, obj in members:
                if isinstance(obj, CharacterData):
                    cdata = obj
                    obj.varname = name
                elif isinstance(obj, Attribute):
                    attrs[obj.name] = obj
                    obj.varname = name
                elif isinstance(obj, (Tag, TagCollection, TagLocalized)):
                    tags[obj.name] = obj
                    obj.varname = name
            if cdata and len(tags) > 0:
                raise TypeError("Class %s defined both CharacterData() and Tag()s" % self.__class__)
            defs = (cdata, attrs, tags)
            self.__class__._autoPiksDefs = defs
        return defs
    
    def _autoPiksParse(self, ctx, doc):
        """Convert XML data to class attributes."""
        cdata, attrs, tags = self._autoPiksScan()
        # Check character data
        if cdata:
            cdata.parse(ctx, doc)
        # Check attributes
        for key in doc.attributes():
            if not key in attrs:
                ctx.error("unknown attribute '%s'" % key)
        for obj in attrs.values():
            obj.parse(ctx, doc)
        # Check tags
        for tag in doc.tags():
            if not tag.name() in tags:
                ctx.error("unknown tag <%s>" % tag.name())
        for obj in tags.values():
            obj.parse(ctx, doc)
        # Custom validation
        if len(ctx.errors) == 0:
            # Since validater functions access members without checking
            # we dont call them if there is already an error.
            validate_func = getattr(self, "validate", None)
            if validate_func:
                validate_func(ctx)
    
    def toString(self, doc=None):
        if not doc:
            doc = piksemel.newDocument(self.root_tag)
            self.toString(doc)
            return doc.toPrettyString()
        
        cdata, attrs, tags = self._autoPiksScan()
        attrs = attrs.values()
        attrs.sort(key=lambda x: x.varname)
        tags = tags.values()
        tags.sort(key=lambda x: x.order)
        
        for attr in attrs:
            attr.serialize(self, doc)
        
        if cdata:
            cdata.serialize(self, doc)
        else:
            for tag in tags:
                tag.serialize(self, doc)
