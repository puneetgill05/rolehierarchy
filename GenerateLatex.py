import argparse
import subprocess
import time
from pathlib import Path

from minedgerolemining.RoleHierarchy import RH


def generate_tikz(nodes_at_levels, edges):
    tikz = [
        "\\begin{tikzpicture}[",
        "  user/.style={circle, draw, fill=blue!10, inner sep=3pt},",
        "  role/.style={diamond, draw, fill=lightgray, inner sep=2pt},",
        "  perm/.style={rectangle, draw, fill=blue!10, inner sep=3pt},",
        "  edge/.style={-, thick},",
        "  node distance=2cm and 3cm,",
        "  every label /.style = {font =\footnotesize}"
    "]\n"
    ]

    # Layer positions
    ctr = 1
    layer_spacing = len(nodes_at_levels)/2

    hspacing = 2
    vspacing = 2
    for nodes_at_level in nodes_at_levels:
        for i, u in enumerate(sorted(nodes_at_level)):
            # for i, u in enumerate(users):
            pos = (hspacing*i, ctr * vspacing)

            n = u[0] + '_{' + u[1:] + '}'
            if u.startswith('u'):
                tikz.append(f"\\node[user] ({u}) at {pos} {{${n}$}};")
            elif u.startswith('p'):
                tikz.append(f"\\node[perm] ({u}) at {pos} {{${n}$}};")
            else:
                tikz.append(f"\\node[role] ({u}) at {pos} {{${n}$}};")

        ctr += 1

    # for i, r in enumerate(roles):
    #     tikz.append(f"\\node[role] (r{i}) at ({i * 2}, 2) {{$r_{{{i}}}$}};")

    # for i, p in enumerate(perms):
    #     tikz.append(f"\\node[perm] (p{i}) at ({i * 2}, 0) {{$p_{{{i}}}$}};")

    tikz.append("")

    # Edges: list of (source_label, target_label)
    for src, tgt in edges:
        tikz.append(f"\\draw[edge] ({src}) -- ({tgt});")

    tikz.append("\\end{tikzpicture}")
    return "\n".join(tikz)


def generate_latex_doc(body: str):
    latex_code = r"""
\documentclass{standalone}
\usepackage{tikz}
\usetikzlibrary{shapes, arrows.meta, positioning}

\begin{document}
\newcommand{\hspacing}{2.5} 
\newcommand{\vspacing}{2.5} 
"""
    # \section*{Multipartite Graph: Users, Roles, Permissions}

    latex_code += body
    latex_code += "\n\n\end{document}"
    return latex_code.strip()


def write_and_compile_latex(latex_code, out_dir):
    tex_filename = "tikz_graph"
    tex_file = Path(f"{out_dir}/{tex_filename}.tex")
    tex_file.write_text(latex_code)
    time.sleep(1)

    try:
        subprocess.run(["pdflatex", "-interaction=nonstopmode", tex_file], check=True, cwd=out_dir)
        print(f"✅ PDF generated: {tex_filename}.pdf")
    except subprocess.CalledProcessError:
        print("❌ pdflatex failed. Check the .log file for details.")


def main():
    parser = argparse.ArgumentParser(description="Read input UP file and generate latex code")
    parser.add_argument("input_file", type=str, help="Input UP file")
    parser.add_argument("levels", type=str, help="Levels")
    parser.add_argument("output_dir", type=str, help="Output Directory")

    args = parser.parse_args()
    nodes_at_levels, edges = RH.get_nodes_at_levels(args.input_file, int(args.levels))
    tikz_code = generate_tikz(nodes_at_levels, edges)
    latex_code = generate_latex_doc(tikz_code)
    write_and_compile_latex(latex_code, args.output_dir)


if __name__ == "__main__":
    main()
