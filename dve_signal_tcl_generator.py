import re
import copy
import itertools
import yaml

###############################
# YAML parser

def clean_data(d):
    """Recursively remove '_line' and '_file' from dicts/lists."""
    if isinstance(d, dict):
        return {k: clean_data(v) for k, v in d.items() if k not in ("_line", "_file")}
    elif isinstance(d, list):
        return [clean_data(v) for v in d]
    else:
        return d

class ParserError(Exception):
    """General exception for any parser error from the YAML config"""
    def __init__(self, message, data=None):
        self.message = message
        self.data = clean_data(data)
        self.line = data.get("_line") if data else None
        self.file = data.get("_file") if data else None
        super().__init__(self.__str__())    # Calls parent class (Exception)

    # Construct string to pass the parent class
    def __str__(self):
        s = self.message
        if self.file:
            s += f" ({self.file}"
            if self.line:
                s += f", line {self.line}"
            s += ")"
        elif self.line:
            s += f" (.yaml file, line {self.line})"
        if self.data is not None:
            s += f". Data: {self.data}"
        return s
    
# Custom loader that keeps track of line numbers. The constructor is added dynamically as recommended by pyYAML
class LineLoader(yaml.SafeLoader):
    pass

def construct_mapping_with_line(loader, node):
    mapping = loader.construct_mapping(node)
    mapping["_line"] = node.start_mark.line + 1  # +1 because line numbers are 0-based
    mapping["_file"] = loader.name  # store filename
    return mapping

LineLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_with_line
)

###############################

# ---------- helpers ----------
def substitute(obj, env):
    """Replace $var and ${var} inside strings, recursively for lists/dicts."""
    if isinstance(obj, str):
        # Replace $var
        for k, v in env.items():
            obj = obj.replace(f"${k}", str(v))
            obj = obj.replace(f"${{{k}}}", str(v))  # handle ${var}
        return obj
    elif isinstance(obj, list):
        return [substitute(x, env) for x in obj]
    elif isinstance(obj, dict):
        return {k: substitute(v, env) for k, v in obj.items()}
    return obj


def expand_iterators(iters, env):
    """Return cartesian product of iterator values merged with env."""
    keys = list(iters.keys())
    ranges = [range(n) for n in iters.values()]
    for values in itertools.product(*ranges):
        new_env = {**env, **dict(zip(keys, values))}
        yield new_env


# ---------- data classes ----------
class Signal:
    def __init__(self, path=None, radix=None, base=None, group=False, signals=None):
        self.path = path          # Actual signal path
        self.radix = radix        # Optional radix
        self.base = base          # Base prefix for grouped signals
        self.group = group        # True if this is a grouped signal
        self.signals = signals or []

    def expand(self, env=None):
        """
        Recursively expand this signal by substituting $var in path using env and flattening grouped signals using base
        Returns a flat list of Signals.
        """
        env = env or {}

        if not self.group:
            # normal signal
            return [Signal(path=substitute(self.path, env), radix=self.radix)]

        # grouped signal
        flat = []
        for s in self.signals:
            for child in s.expand(env):  # recursive
                full_path = f"{substitute(self.base, env)}{child.path}" if child.path else substitute(self.base, env)
                flat.append(Signal(path=full_path, radix=child.radix))
        return flat

    def __repr__(self):
        if self.group:
            return f"SignalGroup(path={self.path}, signals={self.signals})"
        return f"Signal(path={self.path}, radix={self.radix})"

    def __str__(self, indent=0):
        ind = "  " * indent
        if self.group:
            s = f"{ind}base={self.base}"
            if self.signals:
                s += "\n" + "\n".join(child.__str__(indent + 1) for child in self.signals)
            return s
        else:
            s = f"{ind}path={self.path}"
            if self.radix:
                s += f" radix={self.radix}"
            return s

class Group:
    def __init__(self, name, base="", collapse=False, signals=None, subgroups=None, iterators=None, expr=None, parent=None, id=None):
        self.name = name
        self.base = base
        self.collapse = collapse
        self.signals = signals or []
        self.subgroups = subgroups or []
        self.iterators = iterators or {}
        self.expr = expr or {}
        self.parent = parent
        self.id = id
        if self.parent is not None:
            self.full_name = self.parent.name + "|" + self.name 
        else:
            self.full_name = self.name

    @staticmethod
    def parse_signals(raw_signals):
        """
        Parse a list of signal dicts into Signal objects, recursively.
        Replaces the standalone parse_signal function.
        """
        parsed_signals = []
        for s_data in raw_signals:
            if "path" in s_data and s_data["path"]:
                # Normal signal
                parsed_signals.append(Signal(
                    path=s_data["path"],
                    radix=s_data.get("radix")
                ))
            elif "base" in s_data:
                # Grouped signal
                sub_signals = Group.parse_signals(s_data.get("signals", []))
                parsed_signals.append(Signal(
                    path=None,
                    base=s_data["base"],
                    group=True,
                    signals=sub_signals
                ))
            else:
                raise ParserError("Signal missing 'path' or 'base'", s_data)
        return parsed_signals

    @staticmethod
    def parse_group(data, parent=None):
        """
        Parse a single group dict into a Group object.
        """
        if "name" not in data:
            raise ParserError("Group missing 'name' field", data)
        if "base" not in data:
            raise ParserError("Group missing 'base' field", data)

        # Parse iterators
        raw_iterators = clean_data(data.get("iterators", {}))
        iterators = {}
        for k, v in raw_iterators.items():
            if isinstance(v, int):
                iterators[k] = v
            elif isinstance(v, (list, tuple)):
                iterators[k] = list(v)
            elif isinstance(v, dict):
                if "values" not in v:
                    raise ParserError(f"Iterator '{k}' dict must have 'values'", data)
                values = v["values"]
                display = v.get("display", [str(x) for x in values])
                if len(values) != len(display):
                    raise ParserError(f"Iterator '{k}' display and values must have same length", data)
                iterators[k] = {"values": values, "display": display}
            else:
                raise ParserError(f"Iterator '{k}' must be int, sequence, or dict with 'values'", data)

        # Parse expressions
        expr = clean_data(data.get("expr", {}))
        for k, v in expr.items():
            if not isinstance(v, str):
                raise ParserError(f"Expression '{k}' must be a string", data)

        # Parse signals
        flat_signals = []
        if "signals" in data:
            parsed_signals = Group.parse_signals(data["signals"])
            for s in parsed_signals:
                flat_signals.extend(s.expand())


        # Create the Group object
        group_obj = Group(
            name=data["name"],
            base=data.get("base", ""),
            collapse=data.get("collapse", False),
            signals=flat_signals,
            subgroups=[],      # parse separately
            iterators=iterators,
            expr=expr,
            parent=parent
        )

        # Parse subgroups recursively using the method
        group_obj.parse_subgroups(data.get("subgroups", []))
        
        return group_obj
    
    def parse_subgroups(self, raw_subgroups):
        """
        Parse raw subgroup data into Group objects and set parent=self
        """
        parsed = []
        for sg_data in raw_subgroups:
            sg = Group.parse_group(sg_data, parent=self)
            parsed.append(sg)
        self.subgroups = parsed
        return parsed

    def expand(self, env=None):
        env = env or {}

        def expand_iterators():
            """Return a flat list of groups after expanding iterators and expressions."""
            keys = list(self.iterators.keys())
            ranges = [range(v) for v in self.iterators.values()]
            expanded = []
            for values in itertools.product(*ranges):
                iter_env = {**env, **dict(zip(keys, values))}  # add iterator variables
                # Evaluate expressions and add them to env
                for k, expr_str in self.expr.items():
                    try:
                        iter_env[k] = eval(expr_str, {}, iter_env)
                    except Exception as e:
                        raise ParserError(f"Error evaluating expression '{k}: {expr_str}' -> {e}", data={"expr": self.expr})

                g_copy = copy.deepcopy(self)
                g_copy.iterators = {}  # avoid re-expanding
                g_copy.expr = {}       # already expanded
                expanded.extend(g_copy.expand(iter_env))  # pass iter_env
            return expanded

        def expand_signals(base):
            """Return a flat list of signals with full paths usings group's base."""
            flat_signals = []
            for s in self.signals:
                flat_signals.extend(s.expand(env))
            return flat_signals

        def expand_subgroups():
            """Recursively expand subgroups."""
            flat_subgroups = []
            for g in self.subgroups:
                flat_subgroups.extend(g.expand(env))
            return flat_subgroups

        # Stage 1: iterator expansion
        if self.iterators:
            return expand_iterators()

        # Stage 2: substitute env variables
        name = substitute(self.name, env)
        base = substitute(self.base, env)

        # Stage 3: expand signals
        signals = expand_signals(base)

        # Stage 4: expand subgroups
        subgroups = expand_subgroups()

        return [Group(
            name=name, 
            base=base, 
            collapse=self.collapse, 
            signals=signals, 
            subgroups=subgroups,
            parent=self.parent)]    
    
    def tcl_global_signal_groups(self):
        """ 
        Generate the code after the comment:  # Global: Signal Groups
        It creates groups and subgroups, and adds signals to them
        """
        # Self group
        if not self.parent:
            # Top level group
            s = f'''\n### Top level group: {self.name}
set _session_group_{self.id} {{{self.name}}}
gui_sg_create "$_session_group_{self.id}"
set {{{self.name}}} "$_session_group_{self.id}"
'''
        else:
            # Subgroups
            s = f'''# Subgroup: {self.parent.full_name}|{self.name}
set _session_group_{self.id} $_session_group_{self.parent.id}|
append _session_group_{self.id} {{{self.name}}}
gui_sg_create "$_session_group_{self.id}"
set {{{self.parent.full_name}|{self.name}}} "$_session_group_{self.id}"
'''
        # Own signals
        if self.signals:
            s += f'''\ngui_sg_addsignal -group "$_session_group_{self.id} {{ ''' + " ".join(self.base + sig.path for sig in self.signals) + " }\n"
        
        # Signals attributes TODO
        #radix

        # Subgroups
        if self.subgroups:
            for sg in self.subgroups:
                s+= "\n" + sg.tcl_global_signal_groups()
        
        return s
    
    # TODO
    def tcl_view_wave():
        """ 
        Generate the code after the comment: # View 'Wave.1' 
        so signal groups are actually added to the Wave view
        """
        return

    def __repr__(self):
        return f"Group(name={self.name}, base={self.base}, signals={self.signals}, subgroups={self.subgroups})"
    
    def __str__(self, indent=0):
        ind = "  " * indent
        parent_name = self.parent.name if self.parent else ""
        s = f"{ind}Group: {self.name} (base: {self.base}, parent: {parent_name}, id: {self.id})"
        if self.iterators:
            s += f" [iterators: {self.iterators}]"
        if self.signals:
            s += "\n" + "\n".join(f"{ind}  Signal: {sig}" for sig in self.signals)
        if self.subgroups:
            s += "\n" + "\n".join(subgroup.__str__(indent + 1) for subgroup in self.subgroups)
        return s


# ---------- parser ----------
def expand_env(env):
    """Recursively expand $var references inside env itself."""
    changed = True
    while changed:
        changed = False
        for k, v in env.items():
            if isinstance(v, str):
                new_v = v
                for key, val in env.items():
                    if key != k:  # avoid self-substitution
                        new_v = new_v.replace(f"${key}", str(val))
                if new_v != v:
                    env[k] = new_v
                    changed = True
    return env

def fix_parents(groups):
    """
    After expansion and ID assignment, make sure every subgroup's
    parent.id points to the assigned id of its parent object.
    """
    for g in groups:
        for sg in g.subgroups:
            sg.parent = g  # reset parent reference to the expanded parent
            fix_parents([sg])

def assign_ids(groups, start=1):
    """
    Assigns incremental IDs to all groups recursively.
    
    groups: list of Group objects
    start: starting ID (int)
    
    Returns: next available ID after assignment
    """
    current_id = start
    for g in groups:
        g.id = current_id
        current_id += 1
        if g.subgroups:
            current_id = assign_ids(g.subgroups, current_id)
    return current_id

# ---------- usage ----------
if __name__ == "__main__":
    
    # Open yaml file
    with open("sample.yaml") as f:
        raw_cfg = yaml.load(f, Loader=LineLoader)

    # Read env placeholders and expand them (e.g. $core) for substitution later
    env = expand_env(raw_cfg.get("env", {}))

    # List of groups directly parsed
    raw_groups = [Group.parse_group(g) for g in raw_cfg["groups"]]

    

    # Expand subgroups
    groups = []
    for rg in raw_groups:
        groups.extend(rg.expand(env))

    # for g in groups:
    #     set_parent_names(rg)
    
    # Fix parents after flattening
    fix_parents(groups)

    # Assign incremental IDs
    assign_ids(groups, start=1)

    # debug print
    # for g in groups:
    #     print(g)

    # debug print
    for g in groups:
        print(g.tcl_global_signal_groups())
