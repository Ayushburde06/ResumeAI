"""
latex_generator.py  –  Harshibar / jakeryang resume format
https://github.com/jakeryang/resume  (MIT License)

Produces a pixel-perfect .tex that compiles on Overleaf without any edits.
Features:
  • FiraMono fixed-width + tgheros Helvetica-style fonts
  • light-grey / dark-grey color palette
  • \\myuline custom underline for hyperlinks
  • 2 pt light-grey section rules (not black hairline)
  • FontAwesome5 contact icons  (\\faPhone*, \\faEnvelope, \\faLinkedin, \\faGithub, \\faGlobe, \\faMapMarker*)
  • dark-grey color on dates / locations
  • ALL-CAPS section titles
  • Zero extra spaces / no stray blank lines inside tabular environments
  • Every special LaTeX character properly escaped (char-by-char, not str.translate)
  • **bold** markers → \\textbf{}
  • URL underscores NOT escaped inside \\href{}
"""

import re
import textwrap

# ─────────────────────────────────────────────────────────────────────────────
#  Character-level LaTeX escaping
# ─────────────────────────────────────────────────────────────────────────────

# Map every character that needs escaping in LaTeX *body* text.
_ESCAPE_MAP: dict[str, str] = {
    "&":  r"\&",
    "%":  r"\%",
    "$":  r"\$",
    "#":  r"\#",
    "_":  r"\_",
    "{":  r"\{",
    "}":  r"\}",
    "~":  r"\textasciitilde{}",
    "^":  r"\textasciicircum{}",
    "\\": r"\textbackslash{}",
    "<":  r"\textless{}",
    ">":  r"\textgreater{}",
    # Unicode typographic characters
    "\u2013": "--",             # en-dash   –
    "\u2014": "---",            # em-dash   —
    "\u2022": r"\textbullet{}",
    "\u2018": "`",              # '  left single quote
    "\u2019": "'",              # '  right single quote
    "\u201c": "``",             # "  left double quote
    "\u201d": "''",             # "  right double quote
    "\u00a0": "~",              # non-breaking space → tie
    "\u2026": r"\ldots{}",      # …  ellipsis
    "\u00b7": r"\textperiodcentered{}",
    "\u00e9": r"\'{e}",
    "\u00e8": r"\`{e}",
    "\u00e0": r"\`{a}",
    "\u00fc": r'\"{u}',
    "\u00f6": r'\"{o}',
    "\u00e4": r'\"{a}',
}

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def _e(text: object) -> str:
    """Escape arbitrary text for safe LaTeX body inclusion."""
    if text is None:
        return ""
    out: list[str] = []
    for ch in str(text):
        out.append(_ESCAPE_MAP.get(ch, ch))
    return "".join(out)


def _e_url(url: str) -> str:
    """Escape a URL for use inside \\href{}.
    Underscores must NOT be escaped — hyperref handles them.
    Only % needs escaping in URLs."""
    return (url or "").replace("%", r"\%")


def _bold(text: object) -> str:
    """Convert **phrase** → \\textbf{phrase}, escaping all other chars."""
    if text is None:
        return ""
    parts = _BOLD_RE.split(str(text))
    out: list[str] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            out.append(_e(part))
        else:
            out.append(r"\textbf{" + _e(part) + "}")
    return "".join(out)


def _myuline_href(url: str, label: str) -> str:
    """Produce \\href{url}{\\myuline{label}} — the Harshibar link style."""
    return rf"\href{{{_e_url(url)}}}{{\myuline{{{_e(label)}}}}}"


def _shorten(url: str, maxlen: int = 32) -> str:
    """Human-readable URL label."""
    label = (url
             .replace("https://", "")
             .replace("http://", "")
             .replace("www.", "")
             .rstrip("/"))
    return label[:maxlen] + ("…" if len(label) > maxlen else "")


# ─────────────────────────────────────────────────────────────────────────────
#  Preamble  (verbatim copy of the Harshibar template, with dynamic content
#  removed so it stays reusable)
# ─────────────────────────────────────────────────────────────────────────────

_PREAMBLE = textwrap.dedent(r"""
    %-------------------------
    % Resume in Latex
    % Based off of: https://github.com/jakeryang/resume
    % License : MIT
    %------------------------

    \documentclass[letterpaper,11pt]{article}

    \usepackage{latexsym}
    \usepackage[empty]{fullpage}
    \usepackage{titlesec}
    \usepackage{marvosym}
    \usepackage[usenames,dvipsnames]{color}
    \usepackage{verbatim}
    \usepackage{enumitem}
    \usepackage[hidelinks]{hyperref}
    \usepackage{fancyhdr}
    \usepackage[english]{babel}
    \usepackage{tabularx}

    % fontawesome
    \usepackage{fontawesome5}

    % fixed width
    \usepackage[scale=0.90,lf]{FiraMono}

    % light-grey
    \definecolor{light-grey}{gray}{0.83}
    \definecolor{dark-grey}{gray}{0.3}
    \definecolor{text-grey}{gray}{.08}

    \DeclareRobustCommand{\ebseries}{\fontseries{eb}\selectfont}
    \DeclareTextFontCommand{\texteb}{\ebseries}

    % custom underline
    \usepackage{contour}
    \usepackage[normalem]{ulem}
    \renewcommand{\ULdepth}{1.8pt}
    \contourlength{0.8pt}
    \newcommand{\myuline}[1]{%
      \uline{\phantom{#1}}%
      \llap{\contour{white}{#1}}%
    }

    % custom font: helvetica-style
    \usepackage{tgheros}
    \renewcommand*\familydefault{\sfdefault}
    \usepackage[T1]{fontenc}

    \pagestyle{fancy}
    \fancyhf{}
    \fancyfoot{}
    \renewcommand{\headrulewidth}{0pt}
    \renewcommand{\footrulewidth}{0pt}

    % Adjust margins
    \addtolength{\oddsidemargin}{-0.5in}
    \addtolength{\evensidemargin}{0in}
    \addtolength{\textwidth}{1in}
    \addtolength{\topmargin}{-.5in}
    \addtolength{\textheight}{1.0in}

    \urlstyle{same}
    \raggedbottom
    \raggedright
    \setlength{\tabcolsep}{0in}

    % sans-serif section headers with 2pt light-grey rule
    \titleformat{\section}{
        \bfseries \vspace{2pt} \raggedright \large
    }{}{0em}{}[\color{light-grey} {\titlerule[2pt]} \vspace{-4pt}]

    %-------------------------
    % Custom commands
    \newcommand{\resumeItem}[1]{
      \item\small{
        {#1 \vspace{-1pt}}
      }
    }

    \newcommand{\resumeSubheading}[4]{
      \vspace{-1pt}\item
        \begin{tabular*}{\textwidth}[t]{l@{\extracolsep{\fill}}r}
          \textbf{#1} & {\color{dark-grey}\small #2}\vspace{1pt}\\
          \textit{#3} & {\color{dark-grey} \small #4}\\
        \end{tabular*}\vspace{-4pt}
    }

    \newcommand{\resumeSubSubheading}[2]{
        \item
        \begin{tabular*}{\textwidth}{l@{\extracolsep{\fill}}r}
          \textit{\small#1} & \textit{\small #2} \\
        \end{tabular*}\vspace{-7pt}
    }

    \newcommand{\resumeProjectHeading}[2]{
        \item
        \begin{tabular*}{\textwidth}{l@{\extracolsep{\fill}}r}
          #1 & {\color{dark-grey} \small #2} \\
        \end{tabular*}\vspace{-4pt}
    }

    \newcommand{\resumeSubItem}[1]{\resumeItem{#1}\vspace{-4pt}}

    \renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

    \newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0in, label={}]}
    \newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
    \newcommand{\resumeItemListStart}{\begin{itemize}}
    \newcommand{\resumeItemListEnd}{\end{itemize}\vspace{0pt}}

    \color{text-grey}

    %-------------------------------------------
    %%%%%%  RESUME STARTS HERE  %%%%%%%%%%%%%%%%%%%%%%%%%%%%

    \begin{document}
""").lstrip("\n")


# ─────────────────────────────────────────────────────────────────────────────
#  Heading / contact line
# ─────────────────────────────────────────────────────────────────────────────

def _heading(pi: dict) -> list[str]:
    """Produce the centred name + contact icon row."""
    name = _e(pi.get("name") or "Your Name")

    parts: list[str] = []

    if pi.get("phone"):
        parts.append(
            rf"\faPhone* \texttt{{{_e(pi['phone'])}}}"
        )
    if pi.get("email"):
        email_e = _e(pi["email"])
        email_url = _e_url("mailto:" + pi["email"])
        parts.append(
            rf"\faEnvelope \hspace{{2pt}} \texttt{{{email_e}}}"
        )
    if pi.get("linkedin"):
        url = pi["linkedin"].strip()
        label = _e(_shorten(url))
        parts.append(
            rf"\faLinkedin \hspace{{2pt}} {_myuline_href(url, _shorten(url))}"
        )
    if pi.get("github"):
        url = pi["github"].strip()
        parts.append(
            rf"\faGithub \hspace{{2pt}} {_myuline_href(url, _shorten(url))}"
        )
    if pi.get("website"):
        url = pi["website"].strip()
        parts.append(
            rf"\faGlobe \hspace{{2pt}} {_myuline_href(url, _shorten(url))}"
        )
    if pi.get("location"):
        parts.append(
            rf"\faMapMarker* \hspace{{2pt}}\texttt{{{_e(pi['location'])}}}"
        )

    # Join with spaced pipe separators (matches Harshibar style)
    sep = r" \hspace{1pt} $|$ \hspace{1pt} "
    contact_line = sep.join(parts)

    lines: list[str] = [
        r"%----------HEADING----------",
        r"\begin{center}",
        rf"    \textbf{{\Huge {name}}} \\ \vspace{{5pt}}",
        rf"    \small {contact_line}",
        r"    \\ \vspace{-3pt}",
        r"\end{center}",
        "",
    ]
    return lines


# ─────────────────────────────────────────────────────────────────────────────
#  Section entry builders  (return list[str] of lines)
# ─────────────────────────────────────────────────────────────────────────────

def _experience_block(exp: dict) -> list[str]:
    """\\resumeSubheading{Company}{Dates}{Title}{Location} + bullets."""
    company  = _e(exp.get("company") or "")
    title    = _e(exp.get("title") or "")
    location = _e(exp.get("location") or "")
    start    = _e(exp.get("start_date") or "")
    end      = _e(exp.get("end_date") or "")
    date_str = f"{start} -- {end}" if (start and end) else (start or end)
    bullets  = [b for b in (exp.get("bullets") or []) if b]

    # Note the arg order: {Company}{Date}{Title}{Location}  (Harshibar order)
    lines: list[str] = [
        r"    \resumeSubheading",
        f"      {{{company}}}{{{date_str}}}",
        f"      {{{title}}}{{{location}}}",
    ]
    if bullets:
        lines.append(r"      \resumeItemListStart")
        for b in bullets:
            lines.append(f"        \\resumeItem{{{_bold(b)}}}")
        lines.append(r"      \resumeItemListEnd")
    return lines


def _education_block(edu: dict) -> list[str]:
    institution = _e(edu.get("institution") or "")
    location    = _e(edu.get("location") or "")
    degree      = _e(edu.get("degree") or "")
    year        = _e(edu.get("graduation_year") or "")
    gpa         = _e(edu.get("gpa") or "")
    honors      = _e(edu.get("honors") or "")

    extras: list[str] = []
    if gpa:
        extras.append(f"GPA: {gpa}")
    if honors:
        extras.append(honors)
    degree_full = degree + (", " + ", ".join(extras) if extras else "")

    # Harshibar order: {Institution}{Date range}{Degree}{Location}
    lines: list[str] = [
        r"    \resumeSubheading",
        f"      {{{institution}}}{{}}",
        f"      {{{degree_full}}}{{{location}}}",
    ]
    if year:
        # patch: replace empty date with graduation year
        lines[1] = f"      {{{institution}}}{{{year}}}"
    return lines


def _project_block(p: dict) -> list[str]:
    name  = _e(p.get("name") or "")
    link  = (p.get("link") or "").strip()
    live_link = (p.get("live_link") or "").strip()
    desc  = _bold(p.get("description") or "")
    stack = ", ".join(_e(t) for t in (p.get("tech_stack") or []) if t)

    # Project header: bold name with optional link | tech stack on right
    name_tex = rf"\textbf{{{name}}}"
    links: list[str] = []
    if link:
        links.append(rf"{{{_myuline_href(link, _shorten(link))}}}")
    if live_link:
        links.append(rf"{{{_myuline_href(live_link, 'Live Demo')}}}")
        
    if links:
        name_tex += rf" $|$ \small " + " $|$ ".join(links)

    lines: list[str] = [
        r"    \resumeProjectHeading",
        f"      {{{name_tex}}}{{}}",
    ]
    if stack:
        lines.append(f"    \\small{{Built with: {stack}}} \\vspace{{-2pt}}")
    if desc:
        lines.append(r"      \resumeItemListStart")
        lines.append(f"        \\resumeItem{{{desc}}}")
        lines.append(r"      \resumeItemListEnd")
    return lines


def _cert_line(c: dict) -> str:
    name   = _e(c.get("name") or "")
    issuer = _e(c.get("issuer") or "")
    year   = _e(c.get("year") or "")
    extras = [p for p in [issuer, year] if p]
    suffix = (r" $\cdot$ " + ", ".join(extras)) if extras else ""
    return rf"    \resumeItem{{\textbf{{{name}}}{suffix}}}"


# ─────────────────────────────────────────────────────────────────────────────
#  Main generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_latex(resume_data: dict) -> str:
    """
    Convert a TailoredResume dict → fully compilable Harshibar-style LaTeX.

    Sections emitted (when non-empty):
        HEADING, EXPERIENCE, PROJECTS, EDUCATION, SKILLS, CERTIFICATIONS
    """
    pi = resume_data.get("personal_info") or {}

    lines: list[str] = [_PREAMBLE]

    # ── HEADING ──────────────────────────────────────────────────────────────
    lines += _heading(pi)

    # ── EXPERIENCE ───────────────────────────────────────────────────────────
    experience = [e for e in (resume_data.get("experience") or []) if e]
    if experience:
        lines += [
            r"%-----------EXPERIENCE-----------",
            r"\section{EXPERIENCE}",
            r"  \resumeSubHeadingListStart",
            "",
        ]
        for exp in experience:
            lines += _experience_block(exp)
            lines.append("")
        lines += [r"  \resumeSubHeadingListEnd", ""]

    # ── PROJECTS ─────────────────────────────────────────────────────────────
    projects = [p for p in (resume_data.get("projects") or []) if p]
    if projects:
        lines += [
            r"%-----------PROJECTS-----------",
            r"\section{PROJECTS}",
            r"  \resumeSubHeadingListStart",
        ]
        for p in projects:
            lines.append("")
            lines += _project_block(p)
        lines += ["", r"  \resumeSubHeadingListEnd", ""]

    # ── EDUCATION ────────────────────────────────────────────────────────────
    education = [e for e in (resume_data.get("education") or []) if e]
    if education:
        lines += [
            r"%-----------EDUCATION-----------",
            r"\section{EDUCATION}",
            r"  \resumeSubHeadingListStart",
        ]
        for edu in education:
            lines += _education_block(edu)
        lines += [r"  \resumeSubHeadingListEnd", ""]

    # ── SKILLS ───────────────────────────────────────────────────────────────
    skills    = resume_data.get("skills") or {}
    technical = [s for s in (skills.get("technical") or []) if s]
    tools     = [s for s in (skills.get("tools") or []) if s]
    soft      = [s for s in (skills.get("soft") or []) if s]

    skill_rows: list[str] = []
    if technical:
        skill_rows.append(
            r"     \textbf{Languages \& Frameworks}"
            + "{: " + ", ".join(_bold(s) for s in technical) + r"}"
        )
    if tools:
        skill_rows.append(
            r"     \textbf{Systems \& Tools}"
            + "{: " + ", ".join(_bold(s) for s in tools) + r"}"
        )
    if soft:
        skill_rows.append(
            r"     \textbf{Leadership}"
            + "{: " + ", ".join(_bold(s) for s in soft) + r"}"
        )

    if skill_rows:
        lines += [
            r"%-----------SKILLS-----------",
            r"\section{SKILLS}",
            r" \begin{itemize}[leftmargin=0in, label={}]",
            r"    \small{\item{",
        ]
        # Join rows with \\ + \vspace{2pt} — NO trailing \\ on last row
        for idx, row in enumerate(skill_rows):
            if idx < len(skill_rows) - 1:
                lines.append(row + r" \vspace{2pt} \\")
            else:
                lines.append(row)
        lines += [
            r"    }}",
            r" \end{itemize}",
            "",
        ]

    # ── CERTIFICATIONS ───────────────────────────────────────────────────────
    certs = [c for c in (resume_data.get("certifications") or []) if c]
    if certs:
        lines += [
            r"%-----------CERTIFICATIONS-----------",
            r"\section{CERTIFICATIONS}",
            r"  \resumeSubHeadingListStart",
        ]
        for c in certs:
            lines.append(_cert_line(c))
        lines += [r"  \resumeSubHeadingListEnd", ""]

    # ── SUMMARY (if present — placed after skills as an "About" section) ─────
    summary = (resume_data.get("summary") or "").strip()
    if summary:
        lines += [
            r"%-----------SUMMARY-----------",
            r"\section{SUMMARY}",
            rf"\small {_bold(summary)}",
            "",
        ]

    lines.append(r"%-------------------------------------------")
    lines.append(r"\end{document}")

    # Single newline joins — no double blank lines inside logical blocks
    return "\n".join(lines) + "\n"
