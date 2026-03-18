import pygame
import os
import sys
import tkinter as tk
from tkinter import filedialog

def get_col_path(original_path):
    path = os.path.normpath(original_path)
    dirname, basename = os.path.split(path)
    parent_dir, parent_name = os.path.split(dirname)
    
    # Ex: patrol/idle -> col_patrol/idle
    new_parent_name = "col_" + parent_name
    return os.path.join(parent_dir, new_parent_name, basename)

def main():
    # Initialise Tkinter juste pour ouvrir la boite de dialogue
    root = tk.Tk()
    root.withdraw()
    
    print("Sélectionnez le dossier contenant l'animation (ex: patrol/idle)...")
    folder_path = filedialog.askdirectory(title="Sélectionner le dossier d'animation (ex: idle)")
    
    if not folder_path:
        print("Aucun dossier sélectionné. Annulation...")
        sys.exit()
        
    image_files = sorted([f for f in os.listdir(folder_path) if f.endswith('.png')])
    if not image_files:
        print("Aucune image PNG trouvée dans ce dossier.")
        sys.exit()
        
    col_folder_path = get_col_path(folder_path)
    
    if not os.path.exists(col_folder_path):
        print(f"Création du dossier de destination : {col_folder_path}")
        os.makedirs(col_folder_path)

    pygame.init()
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Éditeur de Masque de Collision - Mode Pixel")
    
    font = pygame.font.SysFont("consolas", 18)
    
    images = []
    masks = []
    
    # Charge les images et les éventuels masques existants
    for img_name in image_files:
        img_path = os.path.join(folder_path, img_name)
        img = pygame.image.load(img_path).convert_alpha()
        images.append(img)
        
        mask_path = os.path.join(col_folder_path, img_name)
        if os.path.exists(mask_path):
            mask_img = pygame.image.load(mask_path).convert_alpha()
        else:
            mask_img = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            mask_img.fill((0,0,0,0))
        masks.append(mask_img)

    current_frame = 0
    brush_size = 3
    scale = 10 # Zoom sur l'image
    
    running = True
    clock = pygame.time.Clock()
    
    drawing = False
    erasing = False
    
    def draw_on_mask(pos, erase=False):
        img = images[current_frame]
        img_w, img_h = img.get_size()
        offset_x = (screen_width - img_w * scale) // 2
        offset_y = (screen_height - img_h * scale) // 2
        
        rel_x = (pos[0] - offset_x) // scale
        rel_y = (pos[1] - offset_y) // scale
        
        mask = masks[current_frame]
        
        # Couleur: Rouge opaque pour peindre, transparent pour effacer
        color = (0, 0, 0, 0) if erase else (255, 0, 0, 255)
        pygame.draw.circle(mask, color, (rel_x, rel_y), brush_size)
        
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    drawing = True
                    draw_on_mask(event.pos)
                elif event.button == 3:
                    erasing = True
                    draw_on_mask(event.pos, erase=True)
                elif event.button == 4:
                    brush_size = min(30, brush_size + 1)
                elif event.button == 5:
                    brush_size = max(1, brush_size - 1)
                    
            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    drawing = False
                elif event.button == 3:
                    erasing = False
                    
            if event.type == pygame.MOUSEMOTION:
                if drawing:
                    draw_on_mask(event.pos)
                elif erasing:
                    draw_on_mask(event.pos, erase=True)
                    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    current_frame = (current_frame + 1) % len(images)
                elif event.key == pygame.K_LEFT:
                    current_frame = (current_frame - 1) % len(images)
                elif event.key == pygame.K_c:
                    masks[current_frame].fill((0,0,0,0)) # Effacer tout
                elif event.key == pygame.K_s:
                    # SAUVEGARDER
                    for i, m_name in enumerate(image_files):
                        save_path = os.path.join(col_folder_path, m_name)
                        pygame.image.save(masks[i], save_path)
                    print(f"-> Masques sauvegardés dans {col_folder_path} ! ✅")
                elif event.key == pygame.K_f:
                    # REMPLISSAGE AUTO: prend la forme exacte du sprite
                    img = images[current_frame]
                    mask = masks[current_frame]
                    for x in range(img.get_width()):
                        for y in range(img.get_height()):
                            r, g, b, a = img.get_at((x, y))
                            if a > 127: # Si le pixel d'origine n'est pas transparent
                                mask.set_at((x, y), (255, 0, 0, 255))
                    
        screen.fill((40, 40, 40))
        
        img = images[current_frame]
        mask = masks[current_frame]
        
        img_w, img_h = img.get_size()
        
        # Agrandir l'image et le masque
        scaled_img = pygame.transform.scale(img, (img_w * scale, img_h * scale))
        scaled_mask = pygame.transform.scale(mask, (img_w * scale, img_h * scale))
        
        offset_x = (screen_width - img_w * scale) // 2
        offset_y = (screen_height - img_h * scale) // 2
        
        # Fond "damier" pour bien voir la transparence
        for x in range(0, img_w * scale, 10):
            for y in range(0, img_h * scale, 10):
                color = (60, 60, 60) if ((x // 10) + (y // 10)) % 2 == 0 else (90, 90, 90)
                pygame.draw.rect(screen, color, (offset_x + x, offset_y + y, 10, 10))
        
        screen.blit(scaled_img, (offset_x, offset_y)) 
        
        # Afficher le masque par dessus (légèrement transparent pour voir en dessous)
        temp_mask_surf = scaled_mask.copy()
        temp_mask_surf.set_alpha(160)
        screen.blit(temp_mask_surf, (offset_x, offset_y))
        
        # Affichage du curseur du pinceau
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (255, 255, 255), mouse_pos, brush_size * scale, 1)

        # Instructions UI
        info = [
            f"Image : {current_frame + 1} / {len(images)}   ({image_files[current_frame]})",
            f"Dossier visé : {col_folder_path}",
            f"Taille pinceau : {brush_size} (Molette)",
            "",
            "[CLICK GAUCHE]  Peindre du masque (Rouge)",
            "[CLICK DROIT]   Gommer",
            "[FLECHES <- ->] Passer à l'image suivante",
            "[ C ]           Tout effacer sur cette frame",
            "[ F ]           Remplissage Auto (Calque le Sprite)",
            "[ S ]           SAUVEGARDER TOUT LE DOSSIER"
        ]
        
        for i, text in enumerate(info):
            color = (150, 255, 150) if "[ S ]" in text else (255, 255, 255)
            txt_surf = font.render(text, True, color)
            screen.blit(txt_surf, (15, 15 + i * 25))
            
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
