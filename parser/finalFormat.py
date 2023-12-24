import json
import requests
from datetime import datetime

def load_json_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def get_ens_info(wallet_address):
    url = f"https://api.ensideas.com/ens/resolve/{wallet_address}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("name", "Unknown"), data.get("avatar", "Unknown")
    else:
        return "Unknown", "Unknown"

def fetch_retrolist_data(impact_evaluation_link):
    modified_link = impact_evaluation_link.replace("https://retropgf3.retrolist.app/list", "https://api.retrolist.app/lists")
    response = requests.get(modified_link)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def determine_impact_evaluation_type(item, badgeholder_mapping):
    categories = item.get("body", {}).get("impactCategory", [])
    wallet_address = item.get("attester", "")

    if "PAIRWISE" in categories:
        return "PAIRWISE"
    elif wallet_address in badgeholder_mapping:
        return "BADGEHOLDER"
    else:
        return "OTHER"

def transform_to_list_dto(item, badgeholder_mapping, approval_mapping, projects):
    if item.get("body", {}).get("impactEvaluationLink", "").startswith("https://retropgf3.retrolist.app/list"):
        retrolist_data = fetch_retrolist_data(item["body"]["impactEvaluationLink"])
        if retrolist_data:
            retrolist_data["id"] = retrolist_data["_id"]
            del retrolist_data["_id"]
            return retrolist_data  # This data is already in the desired format

    domain_name, avatar = get_ens_info(item.get("attester", ""))
    impact_evaluation_type = determine_impact_evaluation_type(item, badgeholder_mapping)

    listContent = item.get("body", {}).get("listContent", [])
    listContentParsed = []
    projectsMetadata = []

    for project in listContent:
        # print(project['RPGF3_Application_UID'], project['RPGF3_Application_UID'] in approval_mapping)
        # if not project['RPGF3_Application_UID'] in approval_mapping: continue

        if project['RPGF3_Application_UID'] in approval_mapping:
            project['RPGF3_Application_UID'] = approval_mapping[project['RPGF3_Application_UID']]

        projectMetadata = next((x for x in projects['projects'] if x['id'] == project['RPGF3_Application_UID']), None)

        if not projectMetadata: continue

        projectsMetadata.append({
            "id": projectMetadata['id'],
            "bio": projectMetadata['bio'],
            "displayName": projectMetadata['displayName'],
            "profileImageUrl": projectMetadata['profileImageUrl'],
        })

        listContentParsed.append(project)
    
    if len(listContentParsed) == 0: return None

    return {
        "id": item.get("id"),
        "listName": item.get("header", {}).get("listName", ""),
        "listDescription": item.get("body", {}).get("listDescription", ""),
        "impactEvaluationDescription": item.get("body", {}).get("impactEvaluationDescription", ""),
        "impactEvaluationLink": item.get("body", {}).get("impactEvaluationLink", ""),
        "impactEvaluationType": impact_evaluation_type,
        "listContent": listContentParsed,
        "projectsMetadata": projectsMetadata,
        "walletAddress": item.get("attester", ""),
        "domainName": domain_name,
        "isBadgeholder": impact_evaluation_type == "BADGEHOLDER",
        "attestationUid": item.get("id"),
        "approvalAttestationUid": item.get("id") if impact_evaluation_type == "BADGEHOLDER" else None,
        "categories": item.get("body", {}).get("impactCategory", []),
        "createdAt": datetime.utcfromtimestamp(item.get("time")).isoformat(),
        "updatedAt": datetime.utcfromtimestamp(item.get("time")).isoformat(),
        "revokedAt": datetime.utcfromtimestamp(item.get("revocationTime")).isoformat() if item.get("revocationTime", 0) != 0 else None,
        "avatar": avatar
    }

def transform_header(item):
    return {
        "id": item.get("id"),
        "listName": item.get("listName", ""),
        "impactEvaluationType": item.get("impactEvaluationType", ""),
        "categories": item.get("categories", []),
        "projectsMetadata": list(map(lambda project: {
            "id": project.get("id"),
            "displayName": project.get("displayName"),
            "profileImageUrl": project.get("profileImageUrl", None),
        }, item.get("projectsMetadata", [])))
    }

def filter_data(data):
    filtered_data = []
    seen_links = set()

    for item in data:
        if item.get("revocationTime", 0) > 0:
            continue  # Skip items with revocation time > 0

        ptr_link = item.get("header", {}).get("listMetadataPtr", "")
        if ptr_link in seen_links:
            continue  # Skip duplicated impact evaluation links

        list_name = item.get("header", {}).get("listName", "")
        if list_name.lower().startswith("test list"):
            continue
        if list_name.lower() == "retrolist only":
            continue

        seen_links.add(ptr_link)
        filtered_data.append(item)

    return filtered_data

def save_json_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def main():
    input_file_path = 'raw/attestationsWithBody.json'  # Replace with the path to your input JSON file
    badgeholder_file_path = 'raw/badgeholderAttestation.json'  # Path to badgeholder mapping file
    approval_file_path = 'raw/approveAttestationMapping.json'  # Path to project approval mapping file
    projects_file_path = 'raw/projects.json'  # Path to projects mapping file

    output_file_path = 'lists.json'  # Output file path
    headers_file_path = 'listsHeader.json'  # Output file path

    json_data = load_json_file(input_file_path)
    badgeholder_mapping = load_json_file(badgeholder_file_path)
    approval_mapping = load_json_file(approval_file_path)
    projects = load_json_file(projects_file_path)

    # Filter data before transformation
    filtered_data = filter_data(json_data[::-1])

    # Transform the data to ListDto schema
    transformed_data = [transform_to_list_dto(item, badgeholder_mapping, approval_mapping, projects) for item in filtered_data]
    transformed_data = [item for item in transformed_data if item]

    # Save the transformed data to a JSON file
    save_json_file(transformed_data, output_file_path)

    # Transform to header
    headers = [transform_header(item) for item in transformed_data]

    # Save the transformed data to a JSON file
    save_json_file(headers, headers_file_path)

    # Save each file to lists folder
    for item in transformed_data:
        save_json_file(item, "lists/" + item.get("id") + ".json")
        if item.get("attestationUid") and item.get("attestationUid") != item.get("id"):
            save_json_file(item, "lists/" + item.get("attestationUid") + ".json")

    print(f"Transformed data saved to {output_file_path}")

if __name__ == "__main__":
    main()