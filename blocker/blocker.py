import sys
from csv import reader
from itertools import product, permutations, combinations
from random import shuffle
from operator import attrgetter

import click


# For non-sixth form choices, set speed to 1.
# The program should take under 30 seconds.
# For sixth-form choices, set the speed to a prime number between 20 and 50.
# The lower your prime number...
# ...the more likely it is that a solution will be found...
# ...but the longer it will take. Initial tests took around 5 to 10 minutes.


class Data(object):
    def __init__(self, speed):
        self.speed = int(speed)
        self.students = []
        self.subjects = []
        self.one_class_subjects = []
        self.two_class_subjects = []
        self.multiple_class_subjects = []
        self.subject_dict = {}
        self.no_of_blocks = 0
        self.available_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
        self.allow_free_periods = False


class Subject(object):
    def __init__(self, name, no_of_classes):
        self.name = name
        self.no_of_classes = no_of_classes
        self.students = []
        self.block_choices = []

    @property
    def one_class(self):
        return self.no_of_classes == 1

    @property
    def two_class(self):
        return self.no_of_classes == 2

    @property
    def multiple_class(self):
        return self.no_of_classes > 1



class Student(object):
    def __init__(self, surname, forename, subject_names):
        self.surname, self.forename = surname, forename
        self.subject_names = subject_names
        self.subjects = []
        self.blocks = {}
        self.blocks_inverse = {}
        if '' in self.subject_names:
            self.subject_names.remove('')
            self.subject_names.append('Free')
        if '' in self.subject_names:
            print('%s %s has chosen too few options.'
                    % (self.forename, self.surname))

    def studies_all(self, list_of_subjects):
        for subject in list_of_subjects:
            if not subject in self.subjects:
                return False
        return True


def import_students(student_filename, data):
    with open(student_filename) as student_file:
        for input_line in reader(student_file):
            surname, forename = input_line[0], input_line[1]
            subject_names = input_line[2:]
            student = Student(surname, forename, subject_names)
            if 'Free' in student.subject_names:
                data.allow_free_periods = True
            data.no_of_blocks = max(len(student.subject_names),
                    data.no_of_blocks)
            data.students.append(student)
        data.blocks = data.available_letters[:data.no_of_blocks]


def import_subjects(subject_filename, data):
    with open(subject_filename) as subject_file:
        for name, no_of_classes_str in reader(subject_file):
            subject = Subject(name, int(no_of_classes_str))
            data.subjects.append(subject)
            data.subject_dict[subject.name] = subject
            if subject.no_of_classes == 1:
                data.one_class_subjects.append(subject)
            else:
                data.multiple_class_subjects.append(subject)
            if subject.no_of_classes == 2:
                data.two_class_subjects.append(subject)
    if data.allow_free_periods:
        free = Subject('Free', data.no_of_blocks)
        data.subjects.append(free)
        data.subject_dict['Free'] = free
        data.multiple_class_subjects.append(free)


def process_data(data):
    for student in data.students:
        for subject_name in student.subject_names:
            subject = data.subject_dict[subject_name]
            student.subjects.append(subject)
            subject.students.append(student)

    for subject in data.subjects:
        for comb in combinations(data.blocks, subject.no_of_classes):
            subject.block_choices.append(set(comb))
        subject.no_of_students = len(subject.students)
        subject.students_per_class = (float(subject.no_of_students)
                / subject.no_of_classes)

    data.subjects_by_name = sorted(data.subjects,
            key=attrgetter('name'))
    data.subjects_by_rank = sorted(data.subjects,
            key=attrgetter('no_of_classes', 'no_of_students'))
    for subject, rank in zip(data.subjects_by_rank, range(len(data.subjects))):
        subject.rank = rank
    # This effectively assigns 1 to the least popular subject...
    # ...all the way up to n for the most popular (most classes/students).

    rotation = 0
    for subject in data.subjects:
        rotation += 1
        rotation = rotation % subject.no_of_classes
        subject.block_choices = (subject.block_choices[rotation:]
                 + subject.block_choices[:rotation])
    # This avoids all subjects being biased towards block A/away from block Z.


def find_blocking(data):
    def assign_some_one_class_subjects():
        # This checks for sets of one-class subjects that cannot go together.
        # There are probably quite a few such sets.
        # The biggest such set is picked...
        # ...and its subjects are assigned block A, block B, block C, etc.

        data.assigned_subjects = []
        data.unassigned_subjects = []
        for subject in data.one_class_subjects:
            subject.assigned = False
            data.unassigned_subjects.append(subject)
        assignable_set = set()
        no_to_define = data.no_of_blocks + 1
        best_score = 0
        while no_to_define > 0 and len(assignable_set) == 0:
            for comb in combinations(data.one_class_subjects, no_to_define):
                good_comb = True
                for subject_1, subject_2 in combinations(comb, 2):
                    good_pairing = False
                    for student in data.students:
                        if student.studies_all([subject_1, subject_2]):
                            good_pairing = True
                            break
                    if not good_pairing:
                        good_comb = False
                if good_comb:
                    score = 0
                    for subject in comb:
                        score += subject.no_of_students
                    if score > best_score:
                        best_score = score
                        assignable_set = comb
            no_to_define += -1

        if len(assignable_set) == no_to_define:
            print('This set of choices is impossible to satisfy.')
            data.impossible = True
        for subject, block in zip(assignable_set, data.blocks):
            subject.block_choices = [set(block)]
            subject.assigned = True
            data.assigned_subjects.append(subject)
            data.unassigned_subjects.remove(subject)

    def limit_one_class_subjects():
        # Other one-class subjects have blocks removed that would
        # conflict with the already-assigned subjects.

        for subject in data.unassigned_subjects:
            for subject_1 in data.assigned_subjects:
                for student in data.students:
                    if student.studies_all([subject, subject_1]):
                        to_remove = subject_1.block_choices[0]
                        if to_remove in subject.block_choices:
                            subject.block_choices.remove(to_remove)
                        break

    def limit_two_class_subjects():
        # Two-class subjects have blocks removed that would
        # conflict with the already-assigned subjects.
        for subject in data.two_class_subjects:
            for subject_1, subject_2 in combinations(
                    data.assigned_subjects, 2):
                for student in data.students:
                    if student.studies_all([subject, subject_1, subject_2]):
                        to_remove = subject_1.block_choices[0].union(
                                subject_2.block_choices[0])
                        if to_remove in subject.block_choices:
                            subject.block_choices.remove(to_remove)
                        break

    def satisfies_all_students_1():
        # Check that the current blocking of one-class subjects
        # allows all students to have their options met.
        for student in data.students:
            student_okay = True
            for subject_x, subject_y in combinations(student.subjects, 2):
                if subject_x.one_class and subject_y.one_class:
                    if blocking_dict[subject_x] == blocking_dict[subject_y]:
                        student_okay = False
                        break
            if not student_okay:
                return False
        return True

    def satisfies_all_students():
        # Check that the current blocking of all subjects
        # allows all students to have their options met.
        for student in data.students:
            student_okay = False
            for blocks in permutations(data.blocks):
                permutation_okay = True
                for block, subject in zip(blocks, student.subjects):
                    if block not in blocking_dict[subject]:
                        permutation_okay = False
                        break
                if permutation_okay:
                    student_okay = True
                    break
            if not student_okay:
                return False
        print('this works and is great')
        return True

    def is_balanced():
        # Check that all classes assigned to each block
        # have populations that add to the same total.
        students_per_block = {}
        for block in data.blocks:
            students_per_block[block] = 0
        for subject, blocking in blocking_dict.items():
            for block in blocking:
                students_per_block[block] += int(subject.students_per_class)
                if students_per_block[block] > len(data.students):
                    return False
        return True

    def assign_students_to_classes():
        #If a blocking is good, then randomly assign students to class lists.
        for student in data.students:
            blocks_shuffled = data.blocks[:]
            shuffle(blocks_shuffled)
            student.perms = []
            to_assign = True
            for perm in permutations(blocks_shuffled):
                perm_okay = True
                for block, subject in zip(perm, student.subjects):
                    if block not in blocking_dict[subject]:
                        perm_okay = False
                        break
                if not perm_okay:
                    continue
                student.perms.append(perm)
                if to_assign:
                    for block, subject in zip(perm, student.subjects):
                        student.blocks[block] = subject
                        student.blocks_inverse[subject] = block
                        to_assign = False

    def enumerate_classes():
        counters = {}
        for subject in data.subjects:
            subject.class_counter = {}
            counters[subject] = subject.class_counter
            for block in data.blocks:
                subject.class_counter[block] = 0
        for student in data.students:
            for block, subject in student.blocks.items():
                counters[subject][block] += 1
        return counters

    def make_efficient(counters):
        # Swap blocks for certain students to even up class sizes.
        for subject_0 in data.multiple_class_subjects:
            for student in subject_0.students:
                if (max(counters[subject_0][block] for block in data.blocks)
                        < 1 + subject_0.students_per_class):
                    break
                for perm in student.perms:
                    perm_better = True
                    for new_block, subject in zip(perm, student.subjects):
                        old_block = student.blocks_inverse[subject]
                        if subject == subject_0 and new_block == old_block:
                            perm_better = False
                            break
                        if subject.rank <= subject_0.rank:
                            if ((counters[subject][new_block]
                                    >= counters[subject][old_block])
                                    and new_block != old_block):
                                perm_better = False
                                break
                    if perm_better:
                        for new_block, subject in zip(perm, student.subjects):
                            old_block = student.blocks_inverse[subject]
                            if old_block != new_block:
                                counters[subject][new_block] += 1
                                counters[subject][old_block] += -1
                                student.blocks[new_block] = subject
                                student.blocks_inverse[subject] = new_block
                        break

    def is_perfect(counters):
        # Check for class even-ness.
        for subject in data.subjects:
            sizes = []
            for block, size in subject.class_counter.items():
                if size != 0:
                    sizes.append(size)
            if max(sizes) - min(sizes) > 2:
                return False
        return True

    def print_stats():
        for subject in data.subjects_by_rank:
            stats = subject.name, '; '.join([':'.join(
                    [block, str(counters[subject][block])])
                    for block in data.blocks])
            print(stats)

    data.impossible = False
    assign_some_one_class_subjects()
    limit_one_class_subjects()
    blocking_dict = {}
    if data.impossible:
        return None
    found = False
    one_progress = 0

    # Cycle over all possible blockings of one-class subjects.
    for blockings_1 in product(*[subject.block_choices
                for subject in reversed(data.one_class_subjects)]):
        for subject_1, blocking_1 in zip(
                reversed(data.one_class_subjects), blockings_1):
            blocking_dict[subject_1] = blocking_1
        one_progress += 1
        m_progress = 0
        if one_progress % data.speed != 0:
            continue
        if satisfies_all_students_1():
            print('ones', one_progress)
            limit_two_class_subjects()

            # For each such blocking, cycle over all the other subjects.
            for blockings_m in product(*[subject.block_choices
                    for subject in reversed(data.multiple_class_subjects)]):
                for subject_m, blocking_m in zip(
                        reversed(data.multiple_class_subjects), blockings_m):
                    blocking_dict[subject_m] = blocking_m
                m_progress += 1
                if m_progress % data.speed != 0:
                    continue
                if not is_balanced():
                    continue
                if not satisfies_all_students():
                    continue
                for attempt_no in range(20):
                    assign_students_to_classes()
                    counters = enumerate_classes()
                    make_efficient(counters)
                    perfect = is_perfect(counters)
                    if perfect:
                        break
                if not perfect:
                    continue
                print_stats()
                return True
    return False


def export_blockings(data, blockings_filename):
    blockings_file = open(blockings_filename, 'w')
    for x in range(data.no_of_blocks):
        blockings_file.write('\n')
    first_line = ['Surname', 'Forename']
    for subject in data.subjects_by_rank:
        first_line.append(subject.name)
    blockings_file.write(','.join(first_line))
    blockings_file.write('\n')
    for student in data.students:
        student_line = [student.surname, student.forename]
        for subject in data.subjects_by_rank:
            if subject in student.subjects:
                student_line.append(student.blocks_inverse[subject])
            else:
                student_line.append('')
        blockings_file.write(','.join(student_line))
        blockings_file.write('\n')
    blockings_file.close()


@click.command()
@click.argument(
    'student_filename', metavar='STUDENT_FILENAME',
    type=click.Path(exists=True))
@click.argument(
    'subject_filename', metavar='SUBJECT_FILENAME',
    type=click.Path(exists=True))
@click.option(
    '--output', '-o', metavar='OUTPUT_FILENAME', type=click.Path(),
    default=sys.stdout)
@click.option('--speed', '-s', metavar='SPEED', type=int, default=23)
def main(student_filename, subject_filename, output_filename, speed):
    '''This is a description to tell users what this program does.
    '''
    data = Data(speed)
    import_students(student_filename, data)
    import_subjects(subject_filename, data)
    process_data(data)
    if find_blocking(data):
        export_blockings(data, output_filename)


if __name__ == '__main__':
    main()
