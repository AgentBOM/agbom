"""Docstring parser utility for extracting parameter and return documentation."""

import re
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class ParameterDoc:
    """Documentation for a single parameter."""

    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    default: Optional[str] = None
    required: bool = True


@dataclass
class DocstringInfo:
    """Parsed docstring information."""

    description: Optional[str] = None
    parameters: List[ParameterDoc] = None
    returns: Optional[Dict[str, str]] = None  # {"type": ..., "description": ...}

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []


class DocstringParser:
    """Parser for various docstring formats."""

    @staticmethod
    def parse(docstring: str) -> DocstringInfo:
        """Parse a docstring and extract structured information.

        Supports Google, NumPy, and Sphinx style docstrings.

        Args:
            docstring: The docstring to parse

        Returns:
            DocstringInfo containing parsed information
        """
        if not docstring:
            return DocstringInfo()

        # Clean docstring
        docstring = docstring.strip()

        # Try different parsing styles
        # Google style takes precedence as it's most common
        info = DocstringParser._parse_google_style(docstring)

        if not info.parameters:
            # Try NumPy style
            numpy_info = DocstringParser._parse_numpy_style(docstring)
            if numpy_info.parameters:
                info = numpy_info

        if not info.parameters:
            # Try Sphinx style
            sphinx_info = DocstringParser._parse_sphinx_style(docstring)
            if sphinx_info.parameters:
                info = sphinx_info

        # Extract description if not already found
        if not info.description:
            info.description = DocstringParser._extract_description(docstring)

        return info

    @staticmethod
    def _parse_google_style(docstring: str) -> DocstringInfo:
        """Parse Google-style docstring.

        Example:
            Args:
                param1 (str): Description of param1
                param2 (int, optional): Description of param2. Defaults to 10.

            Returns:
                dict: Description of return value
        """
        info = DocstringInfo()

        # Extract description (text before first section)
        desc_match = re.match(
            r"^(.*?)(?=\n\s*(?:Args?|Parameters?|Returns?|Yields?|Raises?|Note|Notes|Example|Examples|See Also|Attributes?|References?):|$)",
            docstring,
            re.DOTALL,
        )
        if desc_match:
            info.description = desc_match.group(1).strip()

        # Extract Args section
        args_pattern = r"Args?:\s*\n((?:\s+.*\n?)*)"
        args_match = re.search(args_pattern, docstring)

        if args_match:
            args_text = args_match.group(1)

            # Parse individual parameters
            param_pattern = r"^\s+(\w+)\s*(?:\((.*?)\))?\s*:\s*(.*)$"

            current_param = None
            for line in args_text.split("\n"):
                # Check if we've hit the Returns section
                if re.match(r"^\s*Returns?:", line):
                    break

                param_match = re.match(param_pattern, line)
                if param_match:
                    # Save previous param if exists
                    if current_param:
                        info.parameters.append(current_param)

                    name = param_match.group(1)
                    type_info = param_match.group(2) or None
                    desc = param_match.group(3).strip()

                    # Check if optional
                    required = True
                    default = None
                    if type_info:
                        if "optional" in type_info.lower():
                            required = False
                        # Extract type without optional
                        type_clean = re.sub(
                            r",?\s*optional", "", type_info, flags=re.IGNORECASE
                        ).strip()
                        type_info = type_clean if type_clean else None

                    # Check for default value in description
                    default_match = re.search(
                        r"[Dd]efaults?\s+to\s+(.+?)(?:\.|$)", desc
                    )
                    if default_match:
                        default = default_match.group(1).strip()
                        required = False

                    current_param = ParameterDoc(
                        name=name,
                        type=type_info,
                        description=desc,
                        default=default,
                        required=required,
                    )
                elif (
                    current_param
                    and line.strip()
                    and not line.strip().startswith("Returns")
                ):
                    # Continuation of description
                    current_param.description += " " + line.strip()

            # Add last parameter
            if current_param:
                info.parameters.append(current_param)

        # Extract Returns section
        returns_pattern = r"Returns?:\s*\n\s+(.*?)(?:\n\s*\n|\n\s*\w+:|\Z)"
        returns_match = re.search(returns_pattern, docstring, re.DOTALL)

        if returns_match:
            returns_text = returns_match.group(1).strip()

            # Try to parse type and description
            type_desc_match = re.match(r"^(\S+?):\s*(.*)$", returns_text, re.DOTALL)
            if type_desc_match:
                info.returns = {
                    "type": type_desc_match.group(1),
                    "description": type_desc_match.group(2).strip(),
                }
            else:
                info.returns = {"type": "Any", "description": returns_text}

        return info

    @staticmethod
    def _parse_numpy_style(docstring: str) -> DocstringInfo:
        """Parse NumPy-style docstring.

        Example:
            Parameters
            ----------
            param1 : str
                Description of param1
            param2 : int, optional
                Description of param2

            Returns
            -------
            dict
                Description of return value
        """
        info = DocstringInfo()

        # Extract Parameters section
        params_pattern = (
            r"Parameters?\s*\n\s*-+\s*\n((?:.*\n?)*?)(?=\n\s*\w+\s*\n\s*-+|\Z)"
        )
        params_match = re.search(params_pattern, docstring)

        if params_match:
            params_text = params_match.group(1)

            # Parse individual parameters
            param_pattern = r"^(\w+)\s*:\s*(.*?)(?:\n|$)((?:\s+.*\n?)*)"

            for match in re.finditer(param_pattern, params_text, re.MULTILINE):
                name = match.group(1)
                type_info = match.group(2).strip()
                desc = match.group(3).strip() if match.group(3) else ""

                # Check if optional
                required = True
                default = None
                if "optional" in type_info.lower():
                    required = False
                    type_info = re.sub(
                        r",?\s*optional", "", type_info, flags=re.IGNORECASE
                    ).strip()

                # Check for default in description
                default_match = re.search(
                    r"[Dd]efault(?:s)?\s*[:=]\s*(.+?)(?:\.|$)", desc
                )
                if default_match:
                    default = default_match.group(1).strip()
                    required = False

                info.parameters.append(
                    ParameterDoc(
                        name=name,
                        type=type_info if type_info else None,
                        description=desc,
                        default=default,
                        required=required,
                    )
                )

        # Extract Returns section
        returns_pattern = (
            r"Returns?\s*\n\s*-+\s*\n((?:.*\n?)*?)(?=\n\s*\w+\s*\n\s*-+|\Z)"
        )
        returns_match = re.search(returns_pattern, docstring)

        if returns_match:
            returns_text = returns_match.group(1).strip()
            lines = returns_text.split("\n")

            if lines:
                # First line is usually the type
                type_line = lines[0].strip()
                # Rest is description
                desc_lines = lines[1:] if len(lines) > 1 else []
                desc = "\n".join(line.strip() for line in desc_lines).strip()

                info.returns = {
                    "type": type_line if type_line else "Any",
                    "description": desc,
                }

        return info

    @staticmethod
    def _parse_sphinx_style(docstring: str) -> DocstringInfo:
        """Parse Sphinx-style docstring.

        Example:
            :param param1: Description of param1
            :type param1: str
            :param param2: Description of param2
            :type param2: int
            :return: Description of return value
            :rtype: dict
        """
        info = DocstringInfo()

        # Extract parameters
        param_desc_pattern = r":param\s+(\w+):\s*(.*?)(?=:|\Z)"
        param_type_pattern = r":type\s+(\w+):\s*(.*?)(?=:|\Z)"

        # Build parameter descriptions dict
        param_descs = {}
        for match in re.finditer(param_desc_pattern, docstring, re.DOTALL):
            name = match.group(1)
            desc = match.group(2).strip()
            param_descs[name] = desc

        # Build parameter types dict
        param_types = {}
        for match in re.finditer(param_type_pattern, docstring, re.DOTALL):
            name = match.group(1)
            type_info = match.group(2).strip()
            param_types[name] = type_info

        # Combine into ParameterDoc objects
        all_params = set(list(param_descs.keys()) + list(param_types.keys()))
        for name in all_params:
            desc = param_descs.get(name, "")
            type_info = param_types.get(name, None)

            # Check if optional
            required = True
            default = None
            if type_info and "optional" in type_info.lower():
                required = False
                type_info = re.sub(
                    r",?\s*optional", "", type_info, flags=re.IGNORECASE
                ).strip()

            if desc:
                default_match = re.search(
                    r"[Dd]efault(?:s)?\s*[:=]\s*(.+?)(?:\.|$)", desc
                )
                if default_match:
                    default = default_match.group(1).strip()
                    required = False

            info.parameters.append(
                ParameterDoc(
                    name=name,
                    type=type_info,
                    description=desc,
                    default=default,
                    required=required,
                )
            )

        # Extract return information
        return_desc_pattern = r":return(?:s)?:\s*(.*?)(?=:|\Z)"
        return_type_pattern = r":rtype:\s*(.*?)(?=:|\Z)"

        return_desc = None
        return_desc_match = re.search(return_desc_pattern, docstring, re.DOTALL)
        if return_desc_match:
            return_desc = return_desc_match.group(1).strip()

        return_type = None
        return_type_match = re.search(return_type_pattern, docstring, re.DOTALL)
        if return_type_match:
            return_type = return_type_match.group(1).strip()

        if return_desc or return_type:
            info.returns = {
                "type": return_type if return_type else "Any",
                "description": return_desc if return_desc else "",
            }

        return info

    @staticmethod
    def _extract_description(docstring: str) -> Optional[str]:
        """Extract the main description from a docstring.

        Returns the text before any structured sections.
        """
        # Look for text before any section markers
        sections = [
            r"\n\s*Args?:",
            r"\n\s*Parameters?:",
            r"\n\s*Returns?:",
            r"\n\s*Yields?:",
            r"\n\s*Raises?:",
            r"\n\s*Note:",
            r"\n\s*Example:",
            r"\n\s*Examples:",
            r"\n\s*See Also:",
            r"\n\s*Attributes?:",
            r"\n\s*References?:",
            r"\n\s*-{3,}",  # NumPy style separator
            r":param\s+\w+:",
            r":type\s+\w+:",
            r":return:",
            r":rtype:",  # Sphinx
        ]

        pattern = "|".join(sections)
        match = re.search(pattern, docstring)

        if match:
            desc = docstring[: match.start()].strip()
        else:
            desc = docstring.strip()

        # Clean up the description
        lines = desc.split("\n")
        cleaned_lines = [line.strip() for line in lines]
        desc = " ".join(line for line in cleaned_lines if line)

        return desc if desc else None
