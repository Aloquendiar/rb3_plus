import os
import mido
import sys

def get_track_name(track):
    for msg in track:
        if msg.type == 'track_name':
            return msg.name
    return None

def check_venue_events(track, valid_events):
    for msg in track:
        # Check standard text events
        if msg.type == 'text':
            if msg.text in valid_events:
                return True
    return False

def analyze_midi_batch(root_folder):

    required_tracks_config = {
        'PART REAL_KEYS_X': None,
        'PART REAL_KEYS_H': None,
        'PART REAL_KEYS_M': None,
        'PART REAL_KEYS_E': 2,
        'PART KEYS': None,
        'PART KEYS_ANIM_RH': None
    }

    valid_venue_events = {
        '[coop_k_behind]', '[coop_k_near]', '[coop_kv_behind]',
        '[coop_kv_near]', '[coop_bk_behind]', '[coop_bk_near]',
        '[coop_gk_behind]', '[coop_gk_near]', '[directed_keys]',
        '[directed_keys_cam]', '[directed_keys_np]', '[directed_duo_kb]',
        '[directed_duo_kg]', '[directed_duo_kv]'
    }
    
    print("--- Integrity of the keys upgrades ---")

    files_checked = 0
    issues_found = 0

    for root, dirs, files in os.walk(root_folder):
        for filename in files:
            # MIDI files always end with _plus.mid
            if filename.lower().endswith('_plus.mid'):
                files_checked += 1
                full_path = os.path.join(root, filename)
                
                # Logic: "song_plus.mid" -> "song"
                base_name = os.path.splitext(filename)[0]
                clean_name = base_name[:-5] # remove '_plus'
                
                # .milo files do NOT contain _plus
                milo_name = clean_name + ".milo_xbox"
                milo_path = os.path.join(root, milo_name)

                skip_venue_check = False
                # If .milo exists, we SKIP the venue check in the MIDI
                if os.path.exists(milo_path):
                    skip_venue_check = True
                
                errors = []

                try:
                    mid = mido.MidiFile(full_path)

                    track_counts = {}
                    venue_track_found = False
                    venue_event_found = False

                    # Scan tracks
                    for track in mid.tracks:
                        t_name = get_track_name(track)
                        
                        if t_name:
                            track_counts[t_name] = track_counts.get(t_name, 0) + 1
                            
                            # Check VENUE cuts
                            if not skip_venue_check and t_name == 'VENUE':
                                venue_track_found = True
                                if check_venue_events(track, valid_venue_events):
                                    venue_event_found = True

                    # Validate required tracks
                    for req_track, req_count in required_tracks_config.items():
                        actual_count = track_counts.get(req_track, 0)
                        
                        if req_count is not None:
                            # Strict count check (for REAL_KEYS_E)
                            if actual_count != req_count:
                                errors.append(f"Missing or incorrect count for '{req_track}': Found {actual_count}, Expected {req_count}")
                        else:
                            if actual_count < 1:
                                errors.append(f"Missing track: '{req_track}'")

                    # Venue check reporting
                    if skip_venue_check:
                        # Optional: print(f"Skipping VENUE check for {filename} (found {milo_name})")
                        pass
                    else:
                        if not venue_track_found:
                            errors.append("Missing track: 'VENUE' (and no .milo_xbox found)")
                        elif not venue_event_found:
                            errors.append("VENUE track exists but does not contain any camera cuts for the keyboard.")

                    # Report errors per file
                    if errors:
                        issues_found += 1
                        print(f"\n[ERROR] Issue(s) found in: {filename}")
                        for err in errors:
                            print(f" - {err}")

                except Exception as e:
                    print(f"\n[CRITICAL] Error: Could not parse {filename}: {e}")
                    issues_found += 1

    # Final Summary for Git/CI
    print("\n" + "="*40)
    print(f"Files Checked: {files_checked}")
    print(f"Files with Issues: {issues_found}")
    print("="*40)

    if issues_found > 0:
        sys.exit(1)
    else:
        print("Validation successful. No issues found.")
        sys.exit(0)

if __name__ == "__main__":
    target_folder = "Pro Keys (No New Audio)"
    if os.path.exists(target_folder):
        analyze_midi_batch(target_folder)
    else:
        print(f"Error: The folder '{target_folder}' does not exist.")
        sys.exit(1)