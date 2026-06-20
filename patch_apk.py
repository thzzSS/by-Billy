import os
import zipfile
import shutil
import glob
import subprocess

def run_command(command, cwd=None):
    print(f"Executando comando: {" ".join(command)}")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Erro: {result.stderr}")
        raise Exception(f"Comando falhou: {" ".join(command)}")
    print(result.stdout)
    return result.stdout

def patch_apk():
    apk_original_name = "PROXYANDROID_ORIGINAL.apk"
    apk_saida = "proxyandroid_to_sign.apk"
    decompiled_outer_dir = "decompiled_outer_apk"
    decompiled_inner_dir = "decompiled_inner_apk"
    inner_apk_path_in_outer = "res/xml/jshshjkx.xml"
    modified_inner_apk_name = "modified_inner.apk"

    # Certificar que o APK original está presente
    if not os.path.exists(apk_original_name):
        raise Exception(f"Erro: {apk_original_name} não encontrado no diretório do repositório. Por favor, faça upload do APK original para a raiz do seu repositório GitHub.")


    # Limpeza total de qualquer APK no diretório, exceto o original
    for f in glob.glob("*.apk"):
        if f != apk_original_name:
            try:
                os.remove(f)
            except:
                pass

    # Limpar diretórios de decompilação se existirem
    if os.path.exists(decompiled_outer_dir):
        shutil.rmtree(decompiled_outer_dir)
    if os.path.exists(decompiled_inner_dir):
        shutil.rmtree(decompiled_inner_dir)

    # 1. Decompilar o APK original (camada externa)
    print(f"Decompilando {apk_original_name} (camada externa)...")
    run_command(["apktool", "d", apk_original_name, "-o", decompiled_outer_dir])

    # 2. Modificar MainActivity.smali da camada externa
    main_activity_outer_smali_path = os.path.join(decompiled_outer_dir, "smali_classes2", "com", "termux", "MainActivity.smali")
    print(f"Modificando {main_activity_outer_smali_path}...")
    with open(main_activity_outer_smali_path, "r") as f:
        content = f.read()
    
    # Forçar ZTFPH90O7Y22T para true no construtor
    content = content.replace(
        "    const/4 v0, 0x0\n\n    iput-boolean v0, p0, Lcom/termux/MainActivity;->ZTFPH90O7Y22T:Z",
        "    const/4 v0, 0x1\n\n    iput-boolean v0, p0, Lcom/termux/MainActivity;->ZTFPH90O7Y22T:Z"
    )
    with open(main_activity_outer_smali_path, "w") as f:
        f.write(content)

    # 3. Corrigir layouts.xml da camada externa
    layouts_xml_path = os.path.join(decompiled_outer_dir, "res", "values", "layouts.xml")
    if os.path.exists(layouts_xml_path):
        print(f"Corrigindo {layouts_xml_path}...")
        with open(layouts_xml_path, "r") as f:
            content = f.read()
        content = content.replace(
            "<item type=\"layout\" name=\"activity_main\">ۦ/۠.xml</item>",
            "<item type=\"layout\" name=\"activity_main\">@layout/activity_main</item>"
        )
        with open(layouts_xml_path, "w") as f:
            f.write(content)

    # 4. Extrair o APK interno (jshshjkx.xml) do APK original para modificação
    print(f"Extraindo APK interno para modificação...")
    with zipfile.ZipFile(apk_original_name, 'r') as zip_ref:
        zip_ref.extract(inner_apk_path_in_outer, path=".")
    
    # Renomear o APK interno extraído para um nome de arquivo APK válido para o apktool
    extracted_inner_apk_path = os.path.join("res", "xml", "jshshjkx.xml")
    os.rename(extracted_inner_apk_path, modified_inner_apk_name)

    # 5. Decompilar o APK interno
    print(f"Decompilando o APK interno ({modified_inner_apk_name})...")
    run_command(["apktool", "d", modified_inner_apk_name, "-o", decompiled_inner_dir])

    # 6. Modificar MainActivity.smali do APK interno
    main_activity_inner_smali_path = os.path.join(decompiled_inner_dir, "smali", "com", "termux", "MainActivity.smali")
    print(f"Modificando {main_activity_inner_smali_path}...")
    with open(main_activity_inner_smali_path, "r") as f:
        content = f.read()
    
    # Modificar o método onCreate para pular a verificação de login
    # Substituir a chamada para VGIQHG9JRSNVNQ() por PQDF1RCAVIQK2919()
    content = content.replace(
        "invoke-direct {p0}, Lcom/termux/MainActivity;->VGIQHG9JRSNVNQ()V",
        "invoke-direct {p0}, Lcom/termux/MainActivity;->PQDF1RCAVIQK2919()V"
    )
    # Forçar o retorno de F8K3N7M2P9() para true (se for um método que retorna booleano)
    # Se F8K3N7M2P9 for um método void que exibe a tela de login, precisamos evitar sua chamada.
    # Por enquanto, vamos focar na substituição da chamada em onCreate.

    with open(main_activity_inner_smali_path, "w") as f:
        f.write(content)

    # 7. Recompilar o APK interno modificado
    print(f"Recompilando o APK interno modificado...")
    run_command(["apktool", "b", decompiled_inner_dir, "-o", modified_inner_apk_name])

    # 8. Recompilar o APK externo com as modificações
    print(f"Recompilando o APK externo com as modificações...")
    run_command(["apktool", "b", decompiled_outer_dir, "-o", "temp_base.apk"])

    # 9. Remover o arquivo original do ZIP (do temp_base.apk)
    print(f"Removendo arquivo original {inner_apk_path_in_outer} do temp_base.apk...")
    run_command(["zip", "-d", "temp_base.apk", inner_apk_path_in_outer])

    # 10. Inserir o novo arquivo interno modificado no temp_base.apk
    print(f"Inserindo novo APK interno modificado ({modified_inner_apk_name}) no temp_base.apk...")
    with zipfile.ZipFile("temp_base.apk", 'a') as zip_out:
        zip_out.write(modified_inner_apk_name, inner_apk_path_in_outer)

    # 11. Renomear para o APK de saída
    os.rename("temp_base.apk", apk_saida)
    print(f"APK montado e pronto para alinhamento: {apk_saida}")

    # Limpar diretórios decompilados e APK interno temporário
    shutil.rmtree(decompiled_outer_dir)
    shutil.rmtree(decompiled_inner_dir)
    os.remove(modified_inner_apk_name)
    os.remove(apk_original_name)

if __name__ == "__main__":
    patch_apk()
