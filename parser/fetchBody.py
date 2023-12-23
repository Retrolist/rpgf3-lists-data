import json
import requests

def read_json_file(file_path):
    with open(file_path, 'r', encoding="utf8") as file:
        data = json.load(file)
    return data

def fetch_metadata(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        print(f"Success: {url}")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"Timeout: {url}")
        return None
    except requests.RequestException as e:
        print(f"Error: {url}: {e}")
        return None

def simplify_decoded_data(decoded_data_json):
    simplified_data = {}
    for item in decoded_data_json:
        key = item.get('name')
        value = item.get('value', {}).get('value')
        if key and value is not None:
            if key == 'listMetadataPtrType' and isinstance(value, dict):
                value = int(value.get('hex', 0), 16)  # Convert hex to int
            simplified_data[key] = value
    return simplified_data

def parse_attestations(data):
    attestations = data.get('data', {}).get('attestations', [])
    parsed_attestations = []

    for attestation in attestations:
        parsed_attestation = attestation.copy()
        decoded_data_json = json.loads(attestation.get('decodedDataJson', '[]'))

        header = simplify_decoded_data(decoded_data_json)
        parsed_attestation['header'] = header

        list_metadata_ptr = header.get('listMetadataPtr')

        # Fix ipfs URL
        list_metadata_ptr = list_metadata_ptr.strip()
        if list_metadata_ptr.startswith('Qm') or list_metadata_ptr.startswith('ba'):
            list_metadata_ptr = 'https://ipfs.io/ipfs/' + list_metadata_ptr

        if list_metadata_ptr and list_metadata_ptr.startswith("http"):
            metadata = fetch_metadata(list_metadata_ptr)
            if metadata is not None:
                parsed_attestation['body'] = metadata
        else:
            print(f"Skipping, listMetadataPtr is not a valid URL: {list_metadata_ptr}")
            continue

        parsed_attestation['header']['listMetadataPtr'] = list_metadata_ptr
        del parsed_attestation['decodedDataJson']

        parsed_attestations.append(parsed_attestation)

    return parsed_attestations

def main():
    file_path = 'raw/attestations.json'  # Replace with your JSON file path
    output_file_path = 'raw/attestationsWithBody.json'  # Output file path

    data = read_json_file(file_path)
    parsed_attestations = parse_attestations(data)

    # Save parsed attestations to a JSON file
    with open(output_file_path, 'w', encoding="utf8") as outfile:
        json.dump(parsed_attestations, outfile, indent=2)

    print(f"Parsed attestations have been saved to {output_file_path}")


if __name__ == "__main__":
    main()