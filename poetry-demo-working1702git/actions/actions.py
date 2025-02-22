from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import EventType
from rasa_sdk.events import SlotSet, ActiveLoop

# Определяем требования для каждой позиции
POSITION_REQUIREMENTS = {
    "Project Manager": {
        "required_skills": {"управление проектами", "коммуникация", "планирование"},
        "min_experience": 3,
        "max_salary": 250000
    },
    "Data Analyst": {
        "required_skills": {"sql", "анализ данных", "визуализация", "python"},
        "min_experience": 2,
        "max_salary": 180000
    },
    "Data Engineer": {
        "required_skills": {"python", "etl", "apache spark", "hadoop"},
        "min_experience": 3,
        "max_salary": 220000
    },
    "Data Scientist": {
        "required_skills": {"машинное обучение", "python", "tensorflow", "pytorch"},
        "min_experience": 2,
        "max_salary": 300000
    },
    "MLOps Engineer": {
        "required_skills": {"devops", "docker", "kubernetes", "cloud", "ci/cd"},
        "min_experience": 3,
        "max_salary": 280000
    }
}

class ValidateJobApplicationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_job_application_form"

    def validate_expected_salary(
        self,
        value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        if isinstance(value, str):
            import re
            match = re.search(r'\d+', value)
            if match:
                try:
                    return {"expected_salary": float(match.group())}
                except ValueError:
                    dispatcher.utter_message(text="Пожалуйста, введите корректную сумму зарплаты.")
                    return {"expected_salary": None}
            else:
                dispatcher.utter_message(text="Пожалуйста, введите сумму зарплаты в числовом формате.")
                return {"expected_salary": None}
        elif isinstance(value, (int, float)):
            return {"expected_salary": value}
        else:
            dispatcher.utter_message(text="Пожалуйста, введите сумму зарплаты в числовом формате.")
            return {"expected_salary": None}

class ActionEvaluateCandidate(Action):

    def name(self) -> Text:
        return "action_evaluate_candidate"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        position = tracker.get_slot("position")
        skills = tracker.get_slot("skills") or []
        experience = tracker.get_slot("experience") or 0
        expected_salary = tracker.get_slot("expected_salary") or 0
        contact = tracker.get_slot("contact")

        dispatcher.utter_message(text=f"Debug Info - Position: {position}, Skills: {skills}, Experience: {experience}, Expected Salary: {expected_salary}, Contact: {contact}")

        if not position:
            dispatcher.utter_message(text="Позиция не была указана.")
            return [EventType("active_loop", name=None)]

        # Приведение позиции к правильному формату (заглавной буквой)
        position_formatted = position.lower().title()
        requirements = POSITION_REQUIREMENTS.get(position_formatted)

        if not requirements:
            dispatcher.utter_message(text="Мы не нашли позиции, на которую вы подаете заявку.")
            return [EventType("active_loop", name=None)]

        required_skills = set(skill.lower() for skill in requirements["required_skills"])
        min_experience = requirements["min_experience"]
        max_salary = requirements["max_salary"]

        candidate_skills = set(skill.lower().strip() for skill in skills)
        matched_skills = candidate_skills.intersection(required_skills)
        skill_match_ratio = (len(matched_skills) / len(required_skills)) * 100 if required_skills else 0

        experience_ok = float(experience) >= min_experience
        salary_ok = int(expected_salary) <= max_salary

        is_eligible = True
        reasons = []

        if skill_match_ratio < 50:
            is_eligible = False
            reasons.append("недостаточно навыков")
        if not experience_ok:
            is_eligible = False
            reasons.append("недостаточный опыт")
        if not salary_ok:
            is_eligible = False
            reasons.append("ожидаемая зарплата выше допустимой")

        if is_eligible:
            dispatcher.utter_message(text="Вы соответствуете требованиям позиции. Мы свяжемся с вами для дальнейших шагов.")
        else:
            dispatcher.utter_message(text="К сожалению, вы не соответствуете требованиям выбранной позиции по следующим причинам: " + ", ".join(reasons) + ". Спасибо за интерес к нашей компании.")

        # Деактивируем форму
        return [ActiveLoop(None)]

class ActionHandleFallback(Action):
    """Action to handle fallback attempts within the form."""

    def name(self) -> Text:
        return "action_handle_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[EventType]:

        fallback_count = tracker.get_slot("fallback_count") or 0
        max_fallback = 1  # Установите максимальное количество попыток

        if fallback_count < max_fallback:
            dispatcher.utter_message(text="Извините, я вас не понял. Можете переформулировать?")
            return [SlotSet("fallback_count", fallback_count + 1)]
        else:
            dispatcher.utter_message(text="К сожалению, я не могу понять ваш ответ. Пожалуйста, попробуйте позже.")
            return [
                SlotSet("fallback_count", 0),
                ActiveLoop(None)
            ]