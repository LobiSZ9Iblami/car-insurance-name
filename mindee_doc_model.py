import json

from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
import matplotlib
import mplcursors
from matplotlib.font_manager import json_load
from pygments.lexer import words


def extract_words_from_image(image) -> dict:

    model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)

    # image.seek(0)
    # 2. Загружаем документ из файла
    doc = DocumentFile.from_images(image)  # принимает путь к изображению

    # 3. Применяем модель
    result = model(doc)

    # 4. Экспортируем результат в JSON
    result_json = result.export()
    raw_json = json.dumps(result_json, indent=4)

    return raw_json

def extreact_value(json: dict, key: str) -> list:
    parser_json = []

    if isinstance(json, dict):
        for k, v in json.items():
            if k == key:
                parser_json.append(v)
            else:
                parser_json.extend(extreact_value(v, key))
    elif isinstance(json, list):
        for item in json:
            parser_json.extend(extreact_value(item, key))

    noise_words = {"sex", "date", "of", "birth", "nationality", "passport", "united", "states", "amierica", "america",
                   "card", "name", "u.s.a", "issued", "on", "m",
                   "expired", "place", "connecticut", "department", "state", "names", "usa", "*", "no.",
                   "CONNECTICUT,", "ofthe", "states", "fom", "a"}
    clean_list = []
    for i in parser_json:
        if i is not None and not isinstance(i, int) and i.lower() not in noise_words:
            clean_list.append(i)

    # print(clean_list)

    return clean_list


def get_name(clean_list: list) -> str:

    first_name = None
    last_name = None

    for i in range(len(clean_list)):
        if isinstance(clean_list[i], str):
            if clean_list[i].lower() in ["surname", "surame", "nom", "apelidoa", "sumame"]:
                # lastname
                for j in range(i + 1, len(clean_list)):
                    if isinstance(clean_list[j], str) and clean_list[j].isalpha() and clean_list[j].isupper():
                        last_name = clean_list[j]
                        break
            elif clean_list[i].lower() in ["given"]:
                # firstname
                for j in range(i + 1, len(clean_list)):
                    if isinstance(clean_list[j], str) and clean_list[j].isalpha() and clean_list[j].isupper():
                        first_name = clean_list[j]
                        break

    return f"{last_name} {first_name}"


def get_car_plate_num(clean_list: list) -> str:

    # Initialize analyzer
    analyzer = AnalyzerEngine()

    car_number_pattern = Pattern(name="car_number", regex=r"\b[A-Z]{1,3}\d{2,4}[A-Z]{0,2}\d{0,2}\b", score=0.85)
    car_number_recognizer = PatternRecognizer(supported_entity="CAR_NUMBER", patterns=[car_number_pattern])
    analyzer.registry.add_recognizer(car_number_recognizer)

    text = " ".join(clean_list)

    results = analyzer.analyze(text=text, entities=["CAR_NUMBER"], language="en")

    for res in results:
        return text[res.start:res.end]
