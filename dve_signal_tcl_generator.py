import re
import argparse
import copy
import itertools
import yaml
from collections import defaultdict


#############################################################################
# Script arguments

def parseArguments():
    """
    Parse arguments and pass back to main
    """
    parser = argparse.ArgumentParser(
        description="Generate DVE Tcl scripts with groups and signals based on a "
    )

    parser.add_argument(
        "-c", "--config",
        required=True,
        help="YAML configuration file"
    )
    parser.add_argument(
        "-s", "--source",
        required=True,
        help="TCL file to use as a source to insert the code"
    )
    parser.add_argument(
        "-o", "--output",
        required=False,
        help="Name of output .tcl file"
    )

    args = parser.parse_args()

    # If no output given, derive from source
    if args.output is None:
        args.output = f"patched_{args.source}"

    return args


#############################################################################
# YAML parser stuff

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
    

class CustomLoader(yaml.SafeLoader):
    """
    Custom loader that:
     - keeps track of line numbers and file name
     - flattens dictionaries with the flag '!flatten'
    
    The constructor is added dynamically as recommended by pyYAML.
    """
    pass

def construct_mapping_with_line(loader, node):
    mapping = loader.construct_mapping(node)
    mapping["_line"] = node.start_mark.line + 1  # +1 because line numbers are 0-based
    mapping["_file"] = loader.name  # store filename
    return mapping

CustomLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping_with_line
)

class Config:
    """
    Load generic values from the .yaml that are not turned into Groups, Signals, Dividers or others
    """
    # Place holders. 
    # TODO: If managing multiple configs in one run, change this to instance attributes instead of class attributes
    defaults = {}
    settings = {}
    env = {}
    wave_name = ""

    def __init__(self, raw_cfg):
        
        self.raw_cfg = raw_cfg

        # Populate settings
        self.env = self.expand_env()
        self.defaults = self.raw_cfg.get("defaults", {})

        Divider.set_defaults(self.defaults.get("divider_name",  Divider.default_name))
        Group.set_defaults(self.defaults.get("collapse", Group.default_collapse))

        self.settings = self.raw_cfg.get("settings", {})
        
        self.allowed_radices = self.settings.get("allowed_radices")
        if not self.allowed_radices:
            raise ParserError("Allowed_radices missing under settings.", self.settings)
        Signal.set_defaults(self.allowed_radices)

        if "wave_name" not in self.settings:
            raise ParserError("Wave name has to be set under settings (default value used by dve: 'Wave.1').", self.settings)
        else:
            self.wave_name = self.settings["wave_name"]

    @classmethod
    def from_file(cls, yaml_file=None):
        """
        Alternate constructor: load config from a YAML file.
        """
        # Open .yaml config file
        with open(yaml_file) as f:
            raw_cfg = yaml.load(f, Loader=CustomLoader)
        return cls(raw_cfg)

    def expand_env(self):
        """
        Recursively expand $var references inside env itself.
        """
        env = self.raw_cfg.get("env", {})
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

#############################################################################

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


#############################################################################
# ---------- data classes ----------
class Divider:
    """
    """
    default_name = "Divider"

    @staticmethod
    def set_defaults(divider_name=None):
        """Set class-level defaults."""
        if divider_name is not None:
            Divider.default_name = divider_name

    def __init__(self, name='None'):
        self.name = name or Divider.default_name
            

    def expand(self):
        return self

    def tcl_print(self, group_id):
        s = f'''gui_sg_addsignal -group "$_session_group_{group_id}" {{ {self.name} }} -divider\n'''
        return s
    
    def __repr__(self, indent=0):
        ind = "  " * indent
        s = f"{ind} --- Divider(name={self.name}) ---"
        return s

class Signal:
    """
    """
    allowed_radices = ['decimal', 'binary', 'hex', 'oct', 'ascii']  # Default values, overriden by .yaml

    @staticmethod
    def set_defaults(radices=[]):
        """Set class-level defaults."""
        if radices is not None:
            Signal.allowed_radices = radices

    def __init__(self, path=None, radix=None, base=None, is_group=False, children=None):
        self.path = path          # Actual signal path
        self.radix = radix        # Optional radix]

    def expand(self, env=None, base=None):
        """
        Expand this signal by substituting $var in path using env.
        """
        env = env or {}
        base = base or ''
        return [Signal(path=substitute(self.path, env), radix=self.radix)]

    def __repr__(self, indent=0):
        ind = "  " * indent
        s = f"{ind}Signal(path={self.path}, radix={self.radix})"
        return s

class SignalGroup:
    """
    """
    def __init__(self, base=None, children=None):
        self.base = base or ''
        self.children = children or []
    
    def expand(self, env=None, parent_base=None):
        """
        Recursively expand $var in the base and children using env and 
        then return a flat list of children (Signal and Divider).
        """
        env = env or {}
        parent_base = parent_base or ''
        base = f"{parent_base}{substitute(self.base, env)}"
        flat = []

        for child in self.children:
            if isinstance(child, SignalGroup):
                # Recursive call (unlikely?)
                flat.append(child.expand(env, base))
            elif isinstance(child, Signal):
                # Flatten and expand signals
                flat.append(Signal(path=f"{base}{child.path}", radix=child.radix))
            elif isinstance(child, Divider):
                # Ignore dividers
                flat.append(child)
        return flat

    def __repr__(self, indent=0):
        ind = "  " * indent
        s = f"{ind}SignalGroup(base={self.base}, children={self.children})"
        return s

class Group:
    """
    """
    default_collapse = True
    line_limit = 3000

    @staticmethod
    def set_defaults(default_collapse=None, line_limit=None):
        """Set class-level defaults."""
        if default_collapse is not None:
            Group.default_collapse = default_collapse
        if line_limit is not None:
            Group.line_limit = line_limit

    def __init__(self, name, base="", collapse=None, children=None, subgroups=None, iterators=None, expr=None, parent=None, id=None):
        self.name = name
        self.base = base
        self.collapse = collapse if collapse is not None else Group.default_collapse
        self.children = children or []
        self.subgroups = subgroups or []
        self.iterators = iterators or {}
        self.expr = expr or {}
        self.parent = parent
        self.id = id
        if self.parent:
            self.full_name = self.parent.full_name + "|" + self.name 
        else:
            self.full_name = self.name

    @staticmethod
    def parse_children(raw_children):
        """
        Parse a list of children dicts into Signal, SignalGroup or Divider objects, recursively.
        """
        parsed_children = []
        for s_data in raw_children:
            # Divider
            if "divider" in s_data:
                # Dividers should not have more attributes
                extra_keys = set(s_data.keys()) - {"divider", "_file", "_line"}
                if extra_keys:
                    raise ParserError(f"Divider can't have the attributes: {extra_keys}", s_data)
                
                parsed_children.append(Divider(
                    name=s_data.get("divider")
                ))
            # Signal
            elif "path" in s_data and s_data["path"]:
                # Signals should not have more attributes
                extra_keys = set(s_data.keys()) - set(vars(Signal()).keys()) - {"_file", "_line"}
                if extra_keys:
                    raise ParserError(f"Signal can't have the attribures: {extra_keys}", s_data)
                
                if s_data.get("radix") and s_data.get("radix") not in Signal.allowed_radices:
                    raise ParserError(f'''Radix '{s_data["radix"]}' of signal '{s_data["path"]}' is not part of the allowed radices {Signal.allowed_radices}.''', s_data)

                parsed_children.append(Signal(
                    path=s_data["path"],
                    radix=s_data.get("radix")
                ))
            # SignalGroup
            elif "base" in s_data:
                # SignalGroups should not have more attributes
                extra_keys = set(s_data.keys()) - set(vars(SignalGroup()).keys()) - {"_file", "_line"}
                if extra_keys:
                    raise ParserError(f"SignalGroup can't have the attribures: {extra_keys}", s_data)
                
                sub_children = Group.parse_children(s_data.get("children", []))
                parsed_children.append(SignalGroup(
                    base=s_data["base"],
                    children=sub_children
                ))
            else:
                raise ParserError("Signal missing 'path' or 'base'", s_data)
        return parsed_children

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
            else:
                raise ParserError(f"Iterator '{k}' must be an integer'", data)

        # Parse expressions
        expr = clean_data(data.get("expr", {}))
        for k, v in expr.items():
            if not isinstance(v, str):
                raise ParserError(f"Expression '{k}' must be a string", data)

        # Parse children
        flat_children = []
        if "children" in data:
            parsed_children = Group.parse_children(data["children"])
            for s in parsed_children:
                flat_children.extend(s.expand())

        # Create the Group object
        group_obj = Group(
            name=data["name"],
            base=data.get("base"),
            collapse=data.get("collapse"),
            children=flat_children,
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

        def expand_children(base):
            """Return a flat list of children in which all signals are with full paths usings group's base."""
            flat = []
            for c in self.children:
                if isinstance(c, Divider):
                    flat.append(c)
                else:
                    flat.extend(c.expand(env, base))
            return flat

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
        children = expand_children(None)

        # Stage 4: expand subgroups
        subgroups = expand_subgroups()

        return [Group(
            name=name, 
            base=base, 
            collapse=self.collapse, 
            children=children, 
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
set {{{self.name}}} "$_session_group_{self.id}"\n\n'''
        else:
            # Subgroups
            s = f'''# Subgroup: {self.parent.full_name}|{self.name}
set _session_group_{self.id} $_session_group_{self.parent.id}|
append _session_group_{self.id} {{{self.name}}}
gui_sg_create "$_session_group_{self.id}"
set {{{self.parent.full_name}|{self.name}}} "$_session_group_{self.id}"\n\n'''
        
        # Own signals, spliting for dividers and too long lines
        if self.children:
            s += print_command_signals(
                command=f'''gui_sg_addsignal -group "$_session_group_{self.id}" {{ ''', 
                base=self.base, 
                closing='}\n', 
                separator=' ', 
                signals=self.children,
                group_id=self.id,
                line_limit=Group.line_limit,
                use_dividers=True
            )
            
            s += '\n'

            # Group signals by radix
            signals_by_radix = defaultdict(list)
            for sig in self.children:
                if isinstance(sig, Signal) and sig.radix:
                    signals_by_radix[sig.radix].append(sig)

            for radix, sigs in signals_by_radix.items():
                s += print_command_signals(
                    
                    command=f'''gui_set_radix -radix {{{radix}}} -signals {{ ''', 
                    base=self.base, 
                    closing='}\n', 
                    separator=' ', 
                    signals=sigs,
                    group_id=None,
                    line_limit=Group.line_limit,
                    use_dividers=False
                )


        # Subgroups
        if self.subgroups:
            for sg in self.subgroups:
                s+= "\n" + sg.tcl_global_signal_groups()
        
        return s
    
    def tcl_view_group(self, wave, prev_group_name=None):
        """ 
        Generate the code after the comment: # View 'Wave.1' 
        so signal groups are actually added to the Wave view
        """
        prev_group_name = prev_group_name or "New Group"
        s = f'''gui_list_add_group -id ${{{wave}}} -after {{{prev_group_name}}} {{{{{self.full_name}}}}}\n'''
        
        if self.subgroups:
            prev_subgroup = self.full_name
            for sg in self.subgroups:
                s += sg.tcl_view_group(prev_subgroup)
                prev_subgroup = sg.full_name
        return s
    
    def tcl_collapse_group(self, wave):
        """ 
        Generate the code after the comment: # View 'Wave.1' 
        to collapse groups (after they have been added)
        """
        s = ""
        if self.collapse:
            s = f'''gui_list_collapse -id ${{{wave}}} {{{self.full_name}}}\n'''
            if self.subgroups:
                for sg in self.subgroups:
                    s += sg.tcl_collapse_group(wave)
               
        return s

    def __repr__(self):
        return f"Group(name={self.name}, base={self.base}, full_name={self.full_name}, collapse={self.collapse}, children={self.children}, subgroups={self.subgroups}, iterators={self.iterators}, expr={self.expr}, parent={self.parent}, id={self.id})"
    
    def __str__(self, indent=0):
        ind = "  " * indent
        parent_name = self.parent.name if self.parent else ""
        s = f"{ind}Group: {self.name} (full_name: {self.full_name}, base: {self.base}, parent: {parent_name}, id: {self.id}, collapse={self.collapse})"
        if self.iterators:
            s += f" [iterators: {self.iterators}]"
        if self.expr:
            s += f" [expr: {self.expr}]"
        if self.children:
            s += "\n" + "\n".join(f"{ind}  Children: {c}" for c in self.children)
        if self.subgroups:
            s += "\n" + "\n".join(subgroup.__str__(indent + 1) for subgroup in self.subgroups)
        return s

#############################################################################


def fix_parents(groups):
    """
    After expansion and ID assignment, make sure every subgroup's
    parent.id points to the assigned id of its parent object, and subgroups inherit their
    parent.base.
    """
    for g in groups:
        for sg in g.subgroups:
            sg.parent = g  # reset parent reference to the expanded parent
            sg.base = g.base + sg.base
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

def print_command_signals(command='', base='', closing='', separator=' ', signals=None, group_id=None, line_limit=None, use_dividers=False):
    """
    Argument 'signals' could contain objects of different class
    """
    signals = signals or []
    s = ''
    line = command  # keeps track of last line, to measure if longer than limit

    for sig in signals:
        if isinstance(sig, Divider) and use_dividers:
            # close current line and insert divider
            if line:
                s += line + closing
            s += sig.tcl_print(group_id)
            line = ''
        elif isinstance(sig, Signal):
            if not line:
                # Insert first line if chunk is empty
                line = command
            # Add the signal
            line += base + sig.path + separator
            if line_limit and line_limit > 0 and len(line) > line_limit:
                s += line + closing
                line = command
    # End of children. If line is not finished, close it
    if line:
        s += line + closing
    return s

#############################################################################
# Main
def main():
    """
    """
    # Parse arguments
    args = parseArguments()

    # Load .yaml config file
    cfg = Config.from_file(args.config)

    # List of groups directly parsed
    raw_groups = [Group.parse_group(g) for g in cfg.raw_cfg["groups"]]

    # Expand subgroups
    groups = []
    for rg in raw_groups:
        groups.extend(rg.expand(cfg.env))

    # for g in groups:
    #     set_parent_names(rg)
    
    # Fix parents after flattening
    fix_parents(groups)

    # Assign incremental IDs
    assign_ids(groups, start=cfg.settings["starting_id"])

    # # debug print
    # for g in groups:
    #     print(g)

    # prepare the strings to be printed
    global_signal_groups = "# Creating groups and adding signals"
    add_groups = "# Adding groups to the view\n"
    collapse_groups = "# Collapsing groups and its children\n"
    last_group_fullname = "New Group"   # Default starting group
    for g in groups:
        global_signal_groups += g.tcl_global_signal_groups()
        
        add_groups += g.tcl_view_group(wave=cfg.wave_name, prev_group_name=last_group_fullname)
        last_group_fullname = g.full_name
        
        collapse_groups += g.tcl_collapse_group(wave=cfg.wave_name)


    # Load original .tcl script
    with open(args.source) as f:
        lines = f.readlines()

    # Insert strings
    new_lines = []
    for line in lines:
        # Substitute stuff
        if "gui_wv_zoom_timerange" in line:
            new_lines.append(f"# Zooming out\ngui_wv_zoom_outfull -id ${{{Config.wave_name}}}\n")
        # Leave as it is
        else:            
            new_lines.append(line)
        
        # Apend stuff
        if line.strip() == "# Global: Signal Groups":
            new_lines.append("\n" + global_signal_groups)
        if "gui_wv_zoom_timerange -id ${Wave.1}" in line:
            new_lines.append(add_groups + collapse_groups + "\n")

    # Write to new file
    with open(args.output, "w") as f:
        f.writelines(new_lines)

    # print(global_signal_groups)
    # print(add_groups)
    # print(collapse_groups)




# END OF FUNCTIONS

if __name__ == "__main__":
    main()

# END OF FILE