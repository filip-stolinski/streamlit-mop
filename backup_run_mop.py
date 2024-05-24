import streamlit as st
import pandas as pd
import os
import shutil
import zipfile
from helper_functions import (
    smiles_to_mop,
    smiles_to_mol2,
    run_mop,
    check_job_ended_norm,
    pdb_to_mol2,
    extract_atoms_from_smiles,
    substitute_hetatm_atoms,
)

def run_program(smiles: str, name: str) -> str:
    os.makedirs(f"calc/{name}", exist_ok=True)
    os.chdir(f"calc/{name}")

    mop_file = smiles_to_mop(smiles, name)
    out_file = run_mop(mop_file)
    end_norm_file = check_job_ended_norm(out_file)
    if end_norm_file == "SETPI":
        file_for_alva = smiles_to_mol2(smiles, name)
    elif end_norm_file:
        extracted_atoms, temp_pdb_file = extract_atoms_from_smiles(smiles, name)
        substitute_hetatm_atoms(end_norm_file, extracted_atoms)
        file_for_alva = pdb_to_mol2(end_norm_file)
    else:
        st.warning(f"Mopac did not end job normally for {name}")
        file_for_alva = None

    os.chdir("../..")
    return file_for_alva

def reset_state():
    if 'zip_ready' in st.session_state:
        st.session_state['zip_ready'] = False
    if 'zip_filename' in st.session_state:
        st.session_state['zip_filename'] = None

st.title("SMILES Processing App")

# Sidebar components
st.sidebar.header("Upload and Settings")
uploaded_file = st.sidebar.file_uploader("Upload your XLSX file", type=["xlsx"], key="uploaded_file")
if uploaded_file is not None:
    column_options = pd.read_excel(uploaded_file).columns.tolist()
    smiles_column = st.sidebar.selectbox("SMILES Column Name", options=column_options, index=column_options.index("SMILES") if "SMILES" in column_options else 0)
    id_column = st.sidebar.selectbox("ID Column Name", options=column_options, index=column_options.index("ID") if "ID" in column_options else 0)
    load_button = st.sidebar.button("Load File")

if 'load_button_clicked' not in st.session_state:
    st.session_state['load_button_clicked'] = False

if 'load_button' in locals() and (load_button or st.session_state['load_button_clicked']):
    if uploaded_file is not None:
        df = pd.read_excel(uploaded_file)
        filtered_df = df[[id_column, smiles_column]].dropna()
        st.write("Filtered DataFrame:")
        st.dataframe(filtered_df)
        bar_length = len(filtered_df[smiles_column])
        

        if st.button("Run Calculation"):
            output_files = []
            current_bar_length = 0
            progress_text = "Operation in progress. Please wait."
            my_bar = st.progress(0, text=progress_text)

            for smiles, name in zip(filtered_df[smiles_column], filtered_df[id_column]):
                my_bar.progress(current_bar_length/bar_length, text=progress_text)
                file_for_alva = run_program(smiles, name)
                if file_for_alva:
                    output_files.append(f"calc/{name}/{file_for_alva}")
                current_bar_length+=1
            progress_text = "Operation completed!"
            my_bar.progress(current_bar_length/bar_length, text=progress_text)

            if output_files:
                zip_filename = "output_files.zip"
                with zipfile.ZipFile(zip_filename, 'w') as zipf:
                    for file in output_files:
                        zipf.write(file, os.path.basename(file))

                st.session_state['zip_ready'] = True
                st.session_state['zip_filename'] = zip_filename

    st.session_state['load_button_clicked'] = True

if 'zip_ready' in st.session_state and st.session_state['zip_ready']:
    with open(st.session_state['zip_filename'], "rb") as f:
        st.download_button(
            label="Download ZIP",
            data=f,
            file_name=st.session_state['zip_filename'],
            mime="application/zip"
        )

# Cleanup if new file is uploaded or calculation is run again
if uploaded_file or st.button("Run Calculation"):
    if 'zip_ready' in st.session_state and st.session_state['zip_ready']:
        if os.path.exists("calc"):
            shutil.rmtree("calc")
        if st.session_state['zip_filename'] and os.path.exists(st.session_state['zip_filename']):
            os.remove(st.session_state['zip_filename'])
        reset_state()
