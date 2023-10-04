# Unit Test Definitions

## by subject

Given a known triple, create a TRAPI message that looks up the object by the subject.

## inverse by new subject

Given a known triple, create a TRAPI message that inverts the predicate,
then looks up the new object by the new subject (original object).
       
## by object

Given a known triple, create a TRAPI message that looks up the subject by the object.

## raise subject entity

Given a known triple, create a TRAPI message that uses
a parent instance of the original entity and looks up the object.
This only works if a given instance (category) has an identifier (prefix) namespace
bound to some kind of hierarchical class of instances (i.e. ontological structure).

## raise object by subject

Given a known triple, create a TRAPI message that uses the parent
of the original object category and looks up the object by the subject.
    
## raise predicate by subject

Given a known triple, create a TRAPI message that uses the parent
of the original predicate and looks up the object by the subject.
    
