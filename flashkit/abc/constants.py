"""
AVM2 structural constants — multiname kinds, namespace kinds, trait kinds, flags.

All constants follow the naming convention from the AVM2 specification.
Opcode constants live in :mod:`flashkit.abc.opcodes`.

Reference: Adobe AVM2 Overview, Chapters 4.4–4.8.
"""

# ── Multiname kinds ─────────────────────────────────────────────────────────
# Used in MultinameInfo.kind to determine which fields are valid.

CONSTANT_QName       = 0x07  # Qualified name: namespace + name
CONSTANT_QNameA      = 0x0D  # Qualified name (attribute)
CONSTANT_RTQName     = 0x0F  # Runtime qualified name: name only, ns from stack
CONSTANT_RTQNameA    = 0x10  # Runtime qualified name (attribute)
CONSTANT_RTQNameL    = 0x11  # Runtime qualified name (late-bound): both from stack
CONSTANT_RTQNameLA   = 0x12  # Runtime qualified name (late-bound, attribute)
CONSTANT_Multiname   = 0x09  # Multiname: name + namespace set
CONSTANT_MultinameA  = 0x0E  # Multiname (attribute)
CONSTANT_MultinameL  = 0x1B  # Late-bound multiname: name from stack + ns set
CONSTANT_MultinameLA = 0x1C  # Late-bound multiname (attribute)
CONSTANT_TypeName    = 0x1D  # Parameterized type: Vector.<T>

# ── Namespace kinds ─────────────────────────────────────────────────────────
# Used in NamespaceInfo.kind.

CONSTANT_Namespace          = 0x08  # Regular namespace
CONSTANT_PackageNamespace   = 0x16  # Public package namespace
CONSTANT_PackageInternalNs  = 0x17  # Package-internal namespace
CONSTANT_ProtectedNamespace = 0x18  # Protected namespace (class hierarchy)
CONSTANT_ExplicitNamespace  = 0x19  # Explicit namespace (user-defined)
CONSTANT_StaticProtectedNs  = 0x1A  # Static protected namespace
CONSTANT_PrivateNs          = 0x05  # Private namespace (class-scoped)

# ── Trait kinds ─────────────────────────────────────────────────────────────
# Used in TraitInfo.kind (lower 4 bits of the kind byte).
# Upper 4 bits are trait attributes (ATTR_Final=0x01, ATTR_Override=0x02, ATTR_Metadata=0x04).

TRAIT_Slot     = 0  # Instance variable (field)
TRAIT_Method   = 1  # Method
TRAIT_Getter   = 2  # Getter property
TRAIT_Setter   = 3  # Setter property
TRAIT_Class    = 4  # Class definition
TRAIT_Function = 5  # Function (closure)
TRAIT_Const    = 6  # Constant (final field)

# Trait attribute flags (upper 4 bits of kind byte)
ATTR_Final    = 0x01
ATTR_Override = 0x02
ATTR_Metadata = 0x04

# ── Method flags ────────────────────────────────────────────────────────────
# Bitmask flags in MethodInfo.flags.

METHOD_NeedArguments  = 0x01  # Method uses 'arguments' object
METHOD_NeedActivation = 0x02  # Method needs an activation object
METHOD_NeedRest       = 0x04  # Method uses ...rest parameter
METHOD_HasOptional    = 0x08  # Method has optional parameters
METHOD_SetDxns        = 0x40  # Method sets default XML namespace
METHOD_HasParamNames  = 0x80  # Method has debug parameter names

# ── Instance flags ──────────────────────────────────────────────────────────
# Bitmask flags in InstanceInfo.flags.

INSTANCE_Sealed      = 0x01  # Class is sealed (no dynamic properties)
INSTANCE_Final       = 0x02  # Class is final (cannot be subclassed)
INSTANCE_Interface   = 0x04  # Class is an interface
INSTANCE_ProtectedNs = 0x08  # Class has a protected namespace
