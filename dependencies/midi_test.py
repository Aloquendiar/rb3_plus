import os
import mido
import sys
import re

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

def check_trainer_events(track):
    has_begin = False
    has_end = False

    begin_pattern = re.compile(r'\[begin_key song_trainer_key_\d+\]')
    end_pattern = re.compile(r'\[end_key song_trainer_key_\d+\]')

    for msg in track:
        if msg.type == 'text':
            if begin_pattern.match(msg.text):
                has_begin = True
            elif end_pattern.match(msg.text):
                has_end = True
            
            if has_begin and has_end:
                break

    errors = []
    if not has_begin:
        errors.append("No [begin_key song_trainer_key] found in PART REAL_KEYS_X")
    if not has_end:
        errors.append(" No [end_key song_trainer_key] found in PART REAL_KEYS_X")

    return errors

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
    print("Integrity of the keys upgrades")

    files_checked = 0
    issues_found = 0

    for root, dirs, files in os.walk(root_folder):
        for filename in files:
            if filename.lower().endswith(('.mid')):
                files_checked += 1
                full_path = os.path.join(root, filename)
                base_name = os.path.splitext(filename)[0]
                # milo_path = os.path.join(root, base_name + ".milo_xbox")
                milo_name = ""
                if base_name.lower().endswith("_plus"):
                    clean_name = base_name[:-5] # remove _plus
                    milo_name = (clean_name + ".milo_xbox")

                skip_venue_check = False

                # If .milo exists, we SKIP the venue check
                if milo_name and os.path.exists(os.path.join(root, milo_name)):
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
                            
                            # Check Trainers in PART REAL_KEYS_X
                            if t_name == 'PART REAL_KEYS_X':
                                trainer_errors = check_trainer_events(track)
                                if trainer_errors:
                                    errors.extend(trainer_errors)

                    for req_track, req_count in required_tracks_config.items():
                        actual_count = track_counts.get(req_track, 0)
                        
                        if req_count is not None:
                            # Strict count check (for REAL_KEYS_E)
                            if actual_count != req_count:
                                errors.append(f"Missing or incorrect count for '{req_track}': Found {actual_count}, Expected {req_count}")
                        else:
                            if actual_count < 1:
                                errors.append(f"Missing track: '{req_track}'")

                    if skip_venue_check:
                        print(f"Skipping VENUE check for {filename} (found .milo venue)")
                    else:
                        if not venue_track_found:
                            errors.append("Missing track: 'VENUE'")
                        elif not venue_event_found:
                            errors.append("VENUE track exists but does not contain any camera cuts for the keyboard.")

                    # Report errores
                    if errors:
                        issues_found += 1
                        print(f"Error in {filename}")
                        for err in errors:
                            print(f" - {err}")
                    else:
                        pass

                except Exception as e:
                    print(f"Could not parse {filename}: {e}")
                    issues_found += 1

    # Final Summary
    print(f"Files Checked: {files_checked}")
    print(f"Files with Issues: {issues_found}")
    if issues_found > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    if os.path.exists("Pro Keys (No New Audio)"):
        analyze_midi_batch("Pro Keys (No New Audio)")