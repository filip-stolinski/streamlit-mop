import subprocess
import os
# from alvaDescCLIWrapper.alvadesccliwrapper.alvadesc import AlvaDesc
import pandas as pd


def check_ion_type(smiles: str) -> str:
    if "-" in smiles:
        return "Anion"
    elif "+" in smiles:
        return "Cation"
    else:
        return "Neutral"


def check_type_model(smiles: str) -> str:
    if smiles.count(".") >= 2:
        return "error"
    elif smiles.count(".") == 1:
        smiles_subs = smiles.split(".")
        has_plus = False
        has_minus = False
        for sub in smiles_subs:
            if "+" in sub:
                has_plus = True
            if "-" in sub:
                has_minus = True
            if has_plus and has_minus:
                return "ionic"
        return "error"
    elif (
        smiles.count(".") == 0
    ):  # check if for ex. is ok: ClC1C=C(SCC2C=CC=CC=2)C(S(=O)(N)=O)=CC=1C1OC(CN=[N+]=[N-])=NN=1
        return "general"
    else:
        return "error"


def change_keywords(
    filename: str,
    old_string: str = "PUT KEYWORDS HERE",
    keywords: str = "PM7 PRECISE PDBOUT",
) -> None:
    """
    Finds a substring within a file and replaces it with another.
    """

    with open(filename, "r") as file:
        file_contents = file.read()

    new_contents = file_contents.replace(old_string, keywords)

    with open(filename, "w") as file:
        file.write(new_contents)


def filter_lines_after_obab(filename):
    """Removes lines from a file that don't start with a letter or are empty."""

    with open(filename, "r") as infile, open(filename + ".tmp", "w") as outfile:
        for line in infile:
            if not line.strip() or line.strip()[0].isalpha():
                outfile.write(line)

    os.remove(filename)  # Delete the original file
    os.rename(filename + ".tmp", filename)  # Rename the temporary file


def smiles_to_mop(smiles_string: str, name: str) -> str:
    """Converts a SMILES string into a MOPAC .mop file using obabel.
    Args:
        smiles_string (str): The SMILES representation of the molecule.
    Returns:
        str: The name of the generated MOPAC file.
    """
    # Generate base filename (you can customize this)
    base_filename = name.replace(
        " ", "_"
    )  # Simple, but you might want something better
    output_filename = base_filename + ".mop"

    # Construct the obabel command
    obabel_command = (
        f'obabel -ismi -:"{smiles_string}" -omop -O "{output_filename}" --gen3d -h'
    )
    # Execute the obabel command
    subprocess.run(obabel_command, shell=True, check=True)

    change_keywords(output_filename)
    # filter_lines_after_obab(output_filename)

    return output_filename


def smiles_to_mol2(smiles_string: str, name: str) -> str:
    output_filename = name + ".mol2"
    obabel_command = (
        f'obabel -ismi -:"{smiles_string}" -omol2 -O "{output_filename}" --gen3d -h'
    )
    subprocess.run(obabel_command, shell=True, check=True)
    return output_filename


def run_mop(filename: str) -> str:
    # Needs MOPAC env variable in current venv (celery and runserver both running in venv)
    # Like export MOPAC='/home/pies/Desktop/mopac/mopac/build/mopac' in nano venv/bin/activate
    # mopac = os.environ.get('MOPAC')
    mopac = "../../mopac_files/bin/mopac"
    mopac_command = f'{mopac} "{filename}"'
    subprocess.run(mopac_command, shell=True, check=True)
    out_filename = filename.replace(".mop", ".out")
    return out_filename


def check_job_ended_norm(filename: str):
    with open(filename, "r") as file:
        lines = file.readlines()

    pdb_filename = filename.replace(".out", ".pdb")
    # Check lines in reverse order
    for line in lines:
        if "AN ERROR IN ASSIGNING PI-BONDS" in line:
            return "SETPI"
        elif "Error and normal" in line:
            return False
        elif "JOB ENDED NORMALLY" in line:
            return pdb_filename

    return False  # Not found if we reach here


def pdb_to_mol2(pdb_filename: str) -> str:
    sdf_filename = pdb_filename.replace(".pdb", ".mol2")

    obabel_command = f'obabel -ipdb "{pdb_filename}" -omol2 -O "{sdf_filename}"'
    subprocess.run(obabel_command, shell=True, check=True)

    return sdf_filename


# def alva_desc(filename: str, alva_1: bool = False) -> None:
#     if alva_1:
#         aDesc = AlvaDesc("../../alvadesc_files/alva1/bin/alvaDescCLI")
#     else:
#         aDesc = AlvaDesc("../../alvadesc_files/alva2/bin/alvaDescCLI")
#     aDesc.set_input_file(filename, "MDL")
#     if not aDesc.calculate_descriptors(
#         "ALL"
#     ):  # with alvaDesc v2.0.0 you can also use ALL2D keyword
#         print("Error: " + aDesc.get_error())
#     else:
#         res_out = aDesc.get_output()
#         res_desc_names = aDesc.get_output_descriptors()
#         pandas_df = pd.DataFrame(res_out)
#         pandas_df.columns = res_desc_names

#         return pandas_df


def extract_atoms_from_smiles(smiles: str, name: str) -> tuple:
    """Generete a list of atoms from smiles. To be used in pdbout after mopac"""
    # create a temp file to create a list of atoms / obabel
    base_filename = name.replace(" ", "_")
    output_filename = base_filename + "_temp.pdb"
    obabel_command = (
        f'obabel -ismi -:"{smiles}" -opdb -O "{output_filename}" --gen3d -h'
    )
    # Execute the obabel command
    subprocess.run(obabel_command, shell=True, check=True)
    atoms = []
    with open(output_filename, "r") as file:
        for line in file:
            if line.startswith("HETATM"):
                atom_name = line.split()[-1]  # Get the last column
                atoms.append(atom_name)
    return atoms, output_filename


def substitute_hetatm_atoms(file_path: str, atoms_list: list, start_column: int = 77):
    """Substitutes characters in HETATM lines starting from a given column.

    Args:
        file_path: Path to the file containing HETATM records.
        atoms_list: A list of replacement atom names.
        start_column: The column index (starting from 0) where substitution begins.
    Returns:
        A list of the modified file lines.
    """

    new_lines = []
    with open(file_path, "r") as file:
        for line in file:
            if line.startswith("HETATM"):
                atom_index = int(line.split()[1]) - 1
                if atom_index < len(atoms_list):
                    new_atom = atoms_list[atom_index]
                    new_line = line[:start_column] + new_atom + "\n"  # Substitute
                    new_lines.append(new_line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

    with open(file_path, "w") as file:
        file.writelines(new_lines)
